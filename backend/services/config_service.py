"""
Cerberus: The Dark Auditor - 동적 설정 서비스

관리자가 런타임에 수정할 수 있는 설정을 DynamoDB 에 저장/조회합니다.
- 레벨별 문제(domain·question·pass_criteria)
- 게임 파라미터(TIME_LIMIT, P_MAX, W_TIME, W_PROMPT, BEDROCK_MODEL_ID)
- 관리자 비밀번호 해시
- 유지보수 모드 플래그

저장된 값이 없으면 코드의 기본값(LEVEL_CONFIGS, .env)을 사용합니다.
"""

from __future__ import annotations

import copy
import logging
import threading
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Optional

import bcrypt
import boto3
from botocore.exceptions import ClientError

from config import (
    AWS_REGION,
    BEDROCK_MODEL_ID as DEFAULT_BEDROCK_MODEL_ID,
    DYNAMODB_TABLE_NAME,
    P_MAX as DEFAULT_P_MAX,
    TIME_LIMIT as DEFAULT_TIME_LIMIT,
    W_PROMPT as DEFAULT_W_PROMPT,
    W_TIME as DEFAULT_W_TIME,
)
from prompts.auditor_prompt import LEVEL_CONFIGS as DEFAULT_LEVEL_CONFIGS

logger = logging.getLogger(__name__)

CONFIG_TABLE_NAME = f"{DYNAMODB_TABLE_NAME}-config"
CONFIG_ITEM_ID = "MAIN"
DEFAULT_ADMIN_PASSWORD = "mzcadmin"  # 최초 비밀번호 (배포 직후 변경 권장)

# ──────────────────────────────────────────────
# DynamoDB 리소스
# ──────────────────────────────────────────────
_dynamodb = None
_config_table = None
_is_available = False

try:
    _dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
    _config_table = _dynamodb.Table(CONFIG_TABLE_NAME)
    _config_table.load()
    _is_available = True
    logger.info("설정 테이블 '%s' 연결 성공", CONFIG_TABLE_NAME)
except Exception as exc:
    logger.warning("설정 테이블을 사용할 수 없음 (로컬 모드): %s", exc)
    _is_available = False

# ──────────────────────────────────────────────
# 캐시 & 로컬 저장소
# ──────────────────────────────────────────────
_cache: dict[str, Any] = {}
_cache_lock = threading.Lock()
_local_config: dict[str, Any] = {}


def ensure_config_table_exists() -> None:
    """설정 테이블이 없으면 생성 (앱 시작 시 호출)."""
    global _config_table, _is_available

    if _dynamodb is None:
        return

    try:
        _dynamodb.meta.client.describe_table(TableName=CONFIG_TABLE_NAME)
    except ClientError as exc:
        if exc.response["Error"]["Code"] == "ResourceNotFoundException":
            logger.info("설정 테이블 '%s' 생성 중...", CONFIG_TABLE_NAME)
            _config_table = _dynamodb.create_table(
                TableName=CONFIG_TABLE_NAME,
                KeySchema=[{"AttributeName": "config_id", "KeyType": "HASH"}],
                AttributeDefinitions=[
                    {"AttributeName": "config_id", "AttributeType": "S"}
                ],
                ProvisionedThroughput={
                    "ReadCapacityUnits": 5,
                    "WriteCapacityUnits": 5,
                },
            )
            _config_table.wait_until_exists()
            _is_available = True
            logger.info("설정 테이블 '%s' 생성 완료", CONFIG_TABLE_NAME)
        else:
            raise


# ──────────────────────────────────────────────
# 직렬화 헬퍼
# ──────────────────────────────────────────────
def _to_dynamo(obj: Any) -> Any:
    """재귀적으로 float/int → Decimal 변환."""
    if isinstance(obj, bool):
        return obj
    if isinstance(obj, (int, float)):
        return Decimal(str(obj))
    if isinstance(obj, list):
        return [_to_dynamo(x) for x in obj]
    if isinstance(obj, dict):
        return {str(k): _to_dynamo(v) for k, v in obj.items()}
    return obj


def _from_dynamo(obj: Any) -> Any:
    """Decimal → int/float 로 정규화."""
    if isinstance(obj, Decimal):
        return int(obj) if obj == obj.to_integral_value() else float(obj)
    if isinstance(obj, list):
        return [_from_dynamo(x) for x in obj]
    if isinstance(obj, dict):
        return {k: _from_dynamo(v) for k, v in obj.items()}
    return obj


# ──────────────────────────────────────────────
# 기본 설정
# ──────────────────────────────────────────────
def _default_password_hash() -> str:
    return bcrypt.hashpw(
        DEFAULT_ADMIN_PASSWORD.encode("utf-8"), bcrypt.gensalt()
    ).decode("utf-8")


def _default_config() -> dict[str, Any]:
    """코드 기본값으로 채워진 설정 객체."""
    editable_levels = {
        str(level): {
            "domain": cfg["domain"],
            "question": cfg["question"],
            "pass_criteria": list(cfg["pass_criteria"]),
        }
        for level, cfg in DEFAULT_LEVEL_CONFIGS.items()
    }

    return {
        "config_id": CONFIG_ITEM_ID,
        "admin_password_hash": _default_password_hash(),
        "level_configs": editable_levels,
        "game_params": {
            "TIME_LIMIT": DEFAULT_TIME_LIMIT,
            "P_MAX": DEFAULT_P_MAX,
            "W_TIME": DEFAULT_W_TIME,
            "W_PROMPT": DEFAULT_W_PROMPT,
            "BEDROCK_MODEL_ID": DEFAULT_BEDROCK_MODEL_ID,
        },
        "maintenance_mode": False,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


# ──────────────────────────────────────────────
# 저장/로드
# ──────────────────────────────────────────────
def _load_from_storage() -> dict[str, Any]:
    """저장소에서 설정을 읽어옴. 없으면 기본값으로 시드."""
    if not _is_available:
        if not _local_config:
            _local_config.update(_default_config())
        return copy.deepcopy(_local_config)

    try:
        response = _config_table.get_item(Key={"config_id": CONFIG_ITEM_ID})
        item = response.get("Item")
        if not item:
            seed = _default_config()
            _config_table.put_item(Item=_to_dynamo(seed))
            logger.info("설정 테이블에 기본값 시드 완료")
            return seed
        return _from_dynamo(item)
    except Exception as exc:
        logger.error("설정 로드 실패, 기본값 사용: %s", exc)
        return _default_config()


def _save_to_storage(updates: dict[str, Any]) -> None:
    """캐시·저장소에 변경 사항 반영."""
    with _cache_lock:
        current = _cache.get("config")
        if current is None:
            current = _load_from_storage()
        for k, v in updates.items():
            current[k] = v
        current["updated_at"] = datetime.now(timezone.utc).isoformat()
        _cache["config"] = current

    if not _is_available:
        _local_config.clear()
        _local_config.update(current)
        return

    try:
        _config_table.put_item(Item=_to_dynamo(current))
    except Exception as exc:
        logger.error("설정 저장 실패: %s", exc)
        raise


# ──────────────────────────────────────────────
# 공개 API
# ──────────────────────────────────────────────
def get_config() -> dict[str, Any]:
    with _cache_lock:
        if "config" not in _cache:
            _cache["config"] = _load_from_storage()
        return copy.deepcopy(_cache["config"])


def invalidate_cache() -> None:
    with _cache_lock:
        _cache.pop("config", None)


def get_level_config(level: int) -> Optional[dict]:
    levels = get_config().get("level_configs") or {}
    return levels.get(str(level)) or levels.get(level)


def get_all_level_configs() -> dict[int, dict]:
    levels = get_config().get("level_configs") or {}
    return {int(k): v for k, v in levels.items()}


def get_game_params() -> dict[str, Any]:
    return get_config().get("game_params") or {}


def get_bedrock_model_id() -> str:
    return get_game_params().get("BEDROCK_MODEL_ID") or DEFAULT_BEDROCK_MODEL_ID


def is_maintenance_mode() -> bool:
    return bool(get_config().get("maintenance_mode", False))


def set_maintenance_mode(enabled: bool) -> None:
    _save_to_storage({"maintenance_mode": bool(enabled)})


def update_level_config(level: int, level_config: dict) -> None:
    """특정 레벨의 문제 설정을 업데이트 (부분 또는 전체)."""
    cfg = get_config()
    levels = cfg.get("level_configs") or {}
    levels = {str(k): v for k, v in levels.items()}

    existing = levels.get(str(level), {})
    existing.update(
        {k: v for k, v in level_config.items() if k in ("domain", "question", "pass_criteria")}
    )
    levels[str(level)] = existing
    _save_to_storage({"level_configs": levels})


def replace_all_level_configs(new_configs: dict[int, dict]) -> None:
    """모든 레벨 설정을 일괄 교체 (import 기능용)."""
    normalized = {
        str(level): {
            "domain": cfg.get("domain", ""),
            "question": cfg.get("question", ""),
            "pass_criteria": list(cfg.get("pass_criteria", [])),
        }
        for level, cfg in new_configs.items()
    }
    _save_to_storage({"level_configs": normalized})


def update_game_params(params: dict[str, Any]) -> None:
    cfg = get_config()
    existing = cfg.get("game_params") or {}
    # 허용된 키만 반영
    allowed = {"TIME_LIMIT", "P_MAX", "W_TIME", "W_PROMPT", "BEDROCK_MODEL_ID"}
    for k, v in params.items():
        if k in allowed:
            existing[k] = v
    _save_to_storage({"game_params": existing})


def get_admin_password_hash() -> str:
    return get_config().get("admin_password_hash", "")


def set_admin_password_hash(new_hash: str) -> None:
    _save_to_storage({"admin_password_hash": new_hash})


def reset_to_defaults(reset_password: bool = False) -> dict[str, Any]:
    """모든 설정을 코드 기본값으로 복원. 비밀번호는 옵션."""
    new_cfg = _default_config()
    if not reset_password:
        existing_hash = get_admin_password_hash()
        if existing_hash:
            new_cfg["admin_password_hash"] = existing_hash

    if _is_available:
        try:
            _config_table.put_item(Item=_to_dynamo(new_cfg))
        except Exception as exc:
            logger.error("기본값 복원 실패: %s", exc)
            raise
    else:
        _local_config.clear()
        _local_config.update(new_cfg)

    with _cache_lock:
        _cache["config"] = new_cfg

    logger.info("설정을 코드 기본값으로 복원 완료 (비밀번호 초기화: %s)", reset_password)
    return new_cfg
