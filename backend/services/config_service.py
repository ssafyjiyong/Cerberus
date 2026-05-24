"""
Cerberus: The Dark Auditor - 동적 설정 서비스

관리자가 런타임에 수정할 수 있는 설정을 DynamoDB 에 저장/조회합니다.
- 스테이지별 질문 풀(시나리오·답변경로 기반)
- 게임 파라미터(TIME_LIMIT, P_MAX, W_TIME, W_PROMPT, BEDROCK_MODEL_ID)
- 관리자 비밀번호 해시
- 유지보수 모드 플래그

저장된 값이 없으면 코드의 기본값(STAGE_DEFAULTS, .env)을 시드로 사용합니다.

스키마(v2 — 질문 풀 기반):
    level_configs[<stage>] = {
        "title": str,
        "subtitle": str,
        "time_limit": int,       # 0 이면 전역값 사용
        "p_max": int,            # 0 이면 전역값 사용
        "base_score": int,       # 만점 기준 점수
        "questions": [           # 풀
            {
                "id": str,
                "isms_control_id": str,
                "isms_control_title": str,
                "scenario_context": str,
                "auditor_question": str,
                "answer_paths": [...],
                "default_rebuttal": str,
            },
            ...
        ]
    }

v1(legacy) 스키마는 load 시 자동으로 v2 로 마이그레이션합니다.
"""

from __future__ import annotations

import copy
import logging
import random
import secrets
import threading
import uuid
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
from prompts.auditor_prompt import (
    STAGE_DEFAULTS,
    get_default_questions,
    get_default_stage_meta,
    normalize_question,
)

logger = logging.getLogger(__name__)

CONFIG_TABLE_NAME = f"{DYNAMODB_TABLE_NAME}-config"
CONFIG_ITEM_ID = "MAIN"
DEFAULT_ADMIN_PASSWORD = "mzcadmin"  # 최초 비밀번호 (배포 직후 변경 권장)

ALLOWED_STAGES = (1, 2, 3)
ALLOWED_STAGE_META_FIELDS = ("title", "subtitle", "time_limit", "p_max", "base_score")

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


def _build_default_stage(stage: int) -> dict[str, Any]:
    meta = get_default_stage_meta(stage)
    meta["questions"] = get_default_questions(stage)
    return meta


def _ensure_question_id(q: dict) -> dict:
    """질문에 id 가 없으면 uuid 부여."""
    if not q.get("id"):
        q["id"] = uuid.uuid4().hex[:12]
    return q


def _normalize_stage_payload(stage: int, raw: Any) -> dict[str, Any]:
    """
    저장소에서 읽은 스테이지 설정을 표준 형태로 변환.

    v1(legacy) 형식 ({domain, question, pass_criteria, ...}) 이 들어오면 자동으로
    v2 형식의 단일 질문 풀로 마이그레이션합니다.
    """
    defaults = get_default_stage_meta(stage)

    if not isinstance(raw, dict):
        return {**defaults, "questions": get_default_questions(stage)}

    # v1 → v2 마이그레이션 감지
    if "questions" not in raw and ("pass_criteria" in raw or "question" in raw):
        legacy_question = {
            "id": f"legacy-stage-{stage}",
            "isms_control_id": "",
            "isms_control_title": raw.get("domain", ""),
            "scenario_context": (
                f"(이전 버전에서 가져온 질문입니다. 관리자 페이지에서 시나리오를 보강해 주세요.) "
                f"심사 영역: {raw.get('domain', '')}"
            ),
            "auditor_question": raw.get("question", ""),
            "answer_paths": [
                {
                    "id": "legacy-full",
                    "tier": "full",
                    "description": "구버전 통과 기준(키워드 합집합)",
                    "trigger_keywords": [
                        str(c) for c in (raw.get("pass_criteria") or []) if str(c).strip()
                    ],
                    "follow_up": "",
                    "compensating_keywords": [],
                }
            ],
            "default_rebuttal": "근거가 부족합니다. 좀 더 구체적으로 답변해 주십시오.",
        }
        return {
            "title": str(raw.get("title") or defaults["title"]),
            "subtitle": str(raw.get("subtitle") or defaults["subtitle"]),
            "time_limit": _safe_int(raw.get("time_limit"), defaults["time_limit"]),
            "p_max": _safe_int(raw.get("p_max"), defaults["p_max"]),
            "base_score": _safe_int(raw.get("base_score"), defaults["base_score"]),
            "questions": [normalize_question(legacy_question)],
        }

    # v2 정상 케이스
    raw_questions = raw.get("questions") or []
    questions = [_ensure_question_id(normalize_question(q)) for q in raw_questions if isinstance(q, dict)]
    if not questions:
        questions = get_default_questions(stage)
    return {
        "title": str(raw.get("title") or defaults["title"]),
        "subtitle": str(raw.get("subtitle") or defaults["subtitle"]),
        "time_limit": _safe_int(raw.get("time_limit"), defaults["time_limit"]),
        "p_max": _safe_int(raw.get("p_max"), defaults["p_max"]),
        "base_score": _safe_int(raw.get("base_score"), defaults["base_score"]),
        "questions": questions,
    }


def _safe_int(value: Any, fallback: int) -> int:
    try:
        v = int(value)
        return v if v >= 0 else fallback
    except (TypeError, ValueError):
        return fallback


def _default_config() -> dict[str, Any]:
    """코드 기본값으로 채워진 설정 객체."""
    stage_configs = {str(stage): _build_default_stage(stage) for stage in ALLOWED_STAGES}
    # 질문 ID 보강
    for stage_cfg in stage_configs.values():
        for q in stage_cfg["questions"]:
            _ensure_question_id(q)
    return {
        "config_id": CONFIG_ITEM_ID,
        "admin_password_hash": _default_password_hash(),
        "level_configs": stage_configs,
        "game_params": {
            "TIME_LIMIT": DEFAULT_TIME_LIMIT,
            "P_MAX": DEFAULT_P_MAX,
            "W_TIME": DEFAULT_W_TIME,
            "W_PROMPT": DEFAULT_W_PROMPT,
            "BEDROCK_MODEL_ID": DEFAULT_BEDROCK_MODEL_ID,
        },
        "maintenance_mode": False,
        "schema_version": 2,
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


def get_stage_config(stage: int) -> dict[str, Any]:
    """
    스테이지 설정(메타 + 질문 풀)을 정규화하여 반환합니다.
    저장된 값이 없으면 기본 시드를 사용합니다.
    """
    levels = get_config().get("level_configs") or {}
    raw = levels.get(str(stage)) or levels.get(stage)
    return _normalize_stage_payload(stage, raw)


# 하위 호환: 기존 코드가 get_level_config 를 부르는 경우를 위해 alias.
def get_level_config(level: int) -> dict[str, Any]:
    return get_stage_config(level)


def get_all_stage_configs() -> dict[int, dict[str, Any]]:
    levels = get_config().get("level_configs") or {}
    out: dict[int, dict[str, Any]] = {}
    for stage in ALLOWED_STAGES:
        raw = levels.get(str(stage)) or levels.get(stage)
        out[stage] = _normalize_stage_payload(stage, raw)
    return out


def pick_random_question(stage: int) -> dict[str, Any]:
    """스테이지 풀에서 무작위로 질문 1건을 선택."""
    stage_cfg = get_stage_config(stage)
    questions = stage_cfg.get("questions") or []
    if not questions:
        questions = get_default_questions(stage)
    # secrets 가 아닌 random — 분포 무작위면 충분.
    return random.choice(questions)


def get_effective_stage_runtime(stage: int) -> dict[str, Any]:
    """
    런타임에 실제 적용될 스테이지 파라미터 (time_limit, p_max, base_score) + 무작위 질문.
    단계별 값이 0/누락이면 전역 game_params 의 값을 폴백으로 사용합니다.
    """
    stage_cfg = get_stage_config(stage)
    params = get_game_params()
    time_limit = stage_cfg.get("time_limit") or int(params.get("TIME_LIMIT", 300))
    p_max = stage_cfg.get("p_max") or int(params.get("P_MAX", 8))
    return {
        "time_limit": int(time_limit),
        "p_max": int(p_max),
        "base_score": int(stage_cfg.get("base_score") or 1000),
        "title": stage_cfg.get("title", f"Stage {stage}"),
        "subtitle": stage_cfg.get("subtitle", ""),
        "question": pick_random_question(stage),
    }


def get_game_params() -> dict[str, Any]:
    return get_config().get("game_params") or {}


def get_bedrock_model_id() -> str:
    return get_game_params().get("BEDROCK_MODEL_ID") or DEFAULT_BEDROCK_MODEL_ID


def is_maintenance_mode() -> bool:
    return bool(get_config().get("maintenance_mode", False))


def set_maintenance_mode(enabled: bool) -> None:
    _save_to_storage({"maintenance_mode": bool(enabled)})


# ──────────────────────────────────────────────
# 스테이지 메타 수정 (질문은 별도 CRUD 사용)
# ──────────────────────────────────────────────
def update_stage_meta(stage: int, meta_patch: dict[str, Any]) -> None:
    """스테이지의 메타 정보(title, time_limit 등)만 부분 업데이트."""
    if stage not in ALLOWED_STAGES:
        raise ValueError(f"허용되지 않는 stage: {stage}")
    cfg = get_config()
    levels = {str(k): v for k, v in (cfg.get("level_configs") or {}).items()}
    current = _normalize_stage_payload(stage, levels.get(str(stage)))
    for key in ALLOWED_STAGE_META_FIELDS:
        if key in meta_patch:
            current[key] = meta_patch[key]
    levels[str(stage)] = _normalize_stage_payload(stage, current)
    _save_to_storage({"level_configs": levels})


# 하위 호환 — 기존 admin 라우터가 호출하던 함수 시그니처 유지.
# 새 라우터는 update_stage_meta / question CRUD 를 직접 사용.
def update_level_config(level: int, level_config: dict[str, Any]) -> None:
    update_stage_meta(level, level_config)


# ──────────────────────────────────────────────
# 질문 CRUD (스테이지 풀 단위)
# ──────────────────────────────────────────────
def list_questions(stage: int) -> list[dict[str, Any]]:
    return get_stage_config(stage).get("questions") or []


def add_question(stage: int, question: dict[str, Any]) -> dict[str, Any]:
    """스테이지 풀에 새 질문 추가."""
    if stage not in ALLOWED_STAGES:
        raise ValueError(f"허용되지 않는 stage: {stage}")
    new_q = normalize_question(question)
    if not new_q.get("auditor_question"):
        raise ValueError("auditor_question 은 필수입니다.")
    if not new_q.get("answer_paths"):
        raise ValueError("answer_paths 가 비어있습니다. 최소 1개 이상 필요합니다.")
    new_q["id"] = new_q.get("id") or uuid.uuid4().hex[:12]

    cfg = get_config()
    levels = {str(k): v for k, v in (cfg.get("level_configs") or {}).items()}
    stage_cfg = _normalize_stage_payload(stage, levels.get(str(stage)))
    # ID 충돌 방지
    existing_ids = {q["id"] for q in stage_cfg["questions"]}
    while new_q["id"] in existing_ids:
        new_q["id"] = uuid.uuid4().hex[:12]
    stage_cfg["questions"].append(new_q)
    levels[str(stage)] = stage_cfg
    _save_to_storage({"level_configs": levels})
    return new_q


def update_question(stage: int, question_id: str, patch: dict[str, Any]) -> dict[str, Any]:
    """스테이지 풀 내 특정 질문 수정 (전체 교체 방식 — 클라가 완성된 객체를 보낸다고 가정)."""
    if stage not in ALLOWED_STAGES:
        raise ValueError(f"허용되지 않는 stage: {stage}")
    cfg = get_config()
    levels = {str(k): v for k, v in (cfg.get("level_configs") or {}).items()}
    stage_cfg = _normalize_stage_payload(stage, levels.get(str(stage)))

    target_idx = next(
        (i for i, q in enumerate(stage_cfg["questions"]) if q.get("id") == question_id),
        None,
    )
    if target_idx is None:
        raise KeyError(f"질문을 찾을 수 없습니다: {question_id}")

    existing = stage_cfg["questions"][target_idx]
    merged = {**existing, **patch, "id": question_id}
    normalized = normalize_question(merged)
    normalized["id"] = question_id  # id 변경 금지
    if not normalized.get("auditor_question"):
        raise ValueError("auditor_question 은 필수입니다.")
    if not normalized.get("answer_paths"):
        raise ValueError("answer_paths 가 비어있습니다. 최소 1개 이상 필요합니다.")

    stage_cfg["questions"][target_idx] = normalized
    levels[str(stage)] = stage_cfg
    _save_to_storage({"level_configs": levels})
    return normalized


def delete_question(stage: int, question_id: str) -> None:
    """스테이지 풀에서 질문 삭제 (단, 풀이 비게 되면 거부)."""
    if stage not in ALLOWED_STAGES:
        raise ValueError(f"허용되지 않는 stage: {stage}")
    cfg = get_config()
    levels = {str(k): v for k, v in (cfg.get("level_configs") or {}).items()}
    stage_cfg = _normalize_stage_payload(stage, levels.get(str(stage)))
    remaining = [q for q in stage_cfg["questions"] if q.get("id") != question_id]
    if len(remaining) == len(stage_cfg["questions"]):
        raise KeyError(f"질문을 찾을 수 없습니다: {question_id}")
    if not remaining:
        raise ValueError("스테이지 풀에는 최소 1개 이상의 질문이 있어야 합니다.")
    stage_cfg["questions"] = remaining
    levels[str(stage)] = stage_cfg
    _save_to_storage({"level_configs": levels})


# ──────────────────────────────────────────────
# 일괄 교체 (JSON import)
# ──────────────────────────────────────────────
def replace_all_level_configs(new_configs: dict[Any, dict]) -> None:
    """모든 스테이지 설정을 일괄 교체 (관리자 import 기능용)."""
    normalized: dict[str, dict[str, Any]] = {}
    for stage in ALLOWED_STAGES:
        raw = new_configs.get(stage) or new_configs.get(str(stage))
        normalized[str(stage)] = _normalize_stage_payload(stage, raw)
        # 질문 ID 보강
        for q in normalized[str(stage)]["questions"]:
            _ensure_question_id(q)
    _save_to_storage({"level_configs": normalized})


def update_game_params(params: dict[str, Any]) -> None:
    cfg = get_config()
    existing = cfg.get("game_params") or {}
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
