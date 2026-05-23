"""
Cerberus: The Dark Auditor - 게임 로그 서비스

모든 게임 상호작용을 DynamoDB에 기록하여
추후 데이터 분석(취약 항목 파악 등)에 활용합니다.

저장 데이터:
- 세션별 전체 게임 플레이 로그
- 레벨별 답변 내용 및 평가 결과
- 시간/답변 횟수 통계
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Optional

import boto3
from botocore.exceptions import ClientError

from config import AWS_REGION, DYNAMODB_TABLE_NAME
from prompts.auditor_prompt import LEVEL_CONFIGS
from services import config_service

logger = logging.getLogger(__name__)

# 로그 테이블명은 리더보드 테이블 뒤에 -logs 붙인 형태
LOG_TABLE_NAME = f"{DYNAMODB_TABLE_NAME}-logs"

# ──────────────────────────────────────────────
# DynamoDB 리소스 초기화
# ──────────────────────────────────────────────
_dynamodb = None
_log_table = None
_is_available = False

try:
    _dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
    _log_table = _dynamodb.Table(LOG_TABLE_NAME)
    _log_table.load()
    _is_available = True
    logger.info(
        "게임 로그 테이블 '%s' 연결 성공 (리전: %s)", LOG_TABLE_NAME, AWS_REGION
    )
except Exception as exc:
    logger.warning(
        "게임 로그 테이블을 사용할 수 없습니다 (로컬 개발 모드): %s", exc
    )
    _is_available = False

# ──────────────────────────────────────────────
# 로컬 개발용 인메모리 로그 저장소
# ──────────────────────────────────────────────
_local_logs: list[dict[str, Any]] = []


def ensure_log_table_exists() -> None:
    """게임 로그 테이블이 존재하지 않으면 생성합니다 (앱 시작 시 호출)."""
    global _log_table, _is_available

    if _dynamodb is None:
        return

    try:
        _dynamodb.meta.client.describe_table(TableName=LOG_TABLE_NAME)
    except ClientError as exc:
        if exc.response["Error"]["Code"] == "ResourceNotFoundException":
            logger.info("게임 로그 테이블 '%s' 생성 중...", LOG_TABLE_NAME)
            _log_table = _dynamodb.create_table(
                TableName=LOG_TABLE_NAME,
                KeySchema=[
                    {"AttributeName": "session_id", "KeyType": "HASH"},
                    {"AttributeName": "log_id", "KeyType": "RANGE"},
                ],
                AttributeDefinitions=[
                    {"AttributeName": "session_id", "AttributeType": "S"},
                    {"AttributeName": "log_id", "AttributeType": "S"},
                    {"AttributeName": "level", "AttributeType": "N"},
                    {"AttributeName": "created_at", "AttributeType": "S"},
                ],
                GlobalSecondaryIndexes=[
                    {
                        "IndexName": "level-time-index",
                        "KeySchema": [
                            {"AttributeName": "level", "KeyType": "HASH"},
                            {"AttributeName": "created_at", "KeyType": "RANGE"},
                        ],
                        "Projection": {"ProjectionType": "ALL"},
                        "ProvisionedThroughput": {
                            "ReadCapacityUnits": 5,
                            "WriteCapacityUnits": 5,
                        },
                    }
                ],
                ProvisionedThroughput={
                    "ReadCapacityUnits": 5,
                    "WriteCapacityUnits": 10,
                },
            )
            _log_table.wait_until_exists()
            _is_available = True
            logger.info("게임 로그 테이블 '%s' 생성 완료.", LOG_TABLE_NAME)
        else:
            raise


def log_chat_interaction(
    session_id: str,
    level: int,
    domain: str,
    user_message: str,
    ai_status: str,
    ai_message: str,
    prompt_count: int,
    time_used: float,
    level_attempt: int = 1,
    missing_criteria: Optional[list[int]] = None,
    is_level_clear: bool = False,
    is_game_clear: bool = False,
) -> None:
    """
    개별 채팅 상호작용을 기록합니다.

    Args:
        session_id: 세션 ID
        level: 현재 레벨 (1~3)
        domain: 심사 영역명 (예: "물리적 보안 / 단말기 보안")
        user_message: 사용자 답변 원문
        ai_status: AI 평가 결과 ("pass" | "fail")
        ai_message: AI 피드백 메시지
        prompt_count: 현재까지 사용한 총 프롬프트 수
        time_used: 현재까지 경과 시간(초)
        level_attempt: 현재 레벨에서 이번이 몇 번째 시도인지 (취약도 분석용)
        missing_criteria: 불합격 시 충족하지 못한 통과 기준 번호 목록
        is_level_clear: 이 응답으로 레벨을 클리어했는지
        is_game_clear: 이 응답으로 게임을 클리어했는지
    """
    log_entry = {
        "session_id": session_id,
        "log_id": str(uuid.uuid4()),
        "level": level,
        "level_attempt": level_attempt,
        "domain": domain,
        "user_message": user_message,
        "ai_status": ai_status,
        "ai_message": ai_message,
        "missing_criteria": missing_criteria or [],
        "prompt_count": prompt_count,
        "time_used": round(time_used, 2),
        "is_level_clear": is_level_clear,
        "is_game_clear": is_game_clear,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    if not _is_available:
        # 로컬 개발: 인메모리 저장
        _local_logs.append(log_entry)
        logger.info(
            "📝 [로컬 로그] session=%s level=%d attempt=%d status=%s prompt=%d",
            session_id[:8],
            level,
            level_attempt,
            ai_status,
            prompt_count,
        )
        return

    try:
        # Decimal 변환 (DynamoDB는 float 미지원, 숫자/리스트 모두 처리)
        dynamo_item = {}
        for key, value in log_entry.items():
            if isinstance(value, bool):
                dynamo_item[key] = value
            elif isinstance(value, (int, float)):
                dynamo_item[key] = Decimal(str(value))
            elif isinstance(value, list):
                dynamo_item[key] = [Decimal(str(v)) for v in value]
            else:
                dynamo_item[key] = value

        _log_table.put_item(Item=dynamo_item)
        logger.info(
            "📝 [DB 로그] session=%s level=%d status=%s",
            session_id[:8],
            level,
            ai_status,
        )
    except Exception as exc:
        # 분석 로그 적재 실패가 게임 진행을 막아서는 안 되므로 모든 예외를 흡수합니다.
        logger.error("게임 로그 기록 실패 (게임 진행에는 영향 없음): %s", exc)


def log_game_session_summary(
    session_id: str,
    final_level: int,
    is_completed: bool,
    is_game_clear: bool,
    total_prompts: int,
    total_time: float,
    final_score: Optional[int] = None,
    end_reason: str = "clear",
) -> None:
    """
    게임 세션 종료 시 요약 로그를 기록합니다.

    Args:
        session_id: 세션 ID
        final_level: 도달한 최종 레벨
        is_completed: 게임 종료 여부
        is_game_clear: 전체 클리어 여부
        total_prompts: 총 사용 프롬프트 수
        total_time: 총 소요 시간(초)
        final_score: 최종 점수 (클리어 시)
        end_reason: 종료 사유 ("clear" | "timeout" | "prompt_limit")
    """
    summary = {
        "session_id": session_id,
        "log_id": "SUMMARY",
        "level": final_level,
        "domain": "SESSION_SUMMARY",
        "user_message": "",
        "ai_status": "clear" if is_game_clear else "failed",
        "ai_message": f"End reason: {end_reason}",
        "prompt_count": total_prompts,
        "time_used": round(total_time, 2),
        "is_level_clear": False,
        "is_game_clear": is_game_clear,
        "final_score": final_score,
        "end_reason": end_reason,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    if not _is_available:
        _local_logs.append(summary)
        logger.info(
            "📊 [로컬 요약] session=%s level=%d clear=%s score=%s reason=%s",
            session_id[:8],
            final_level,
            is_game_clear,
            final_score,
            end_reason,
        )
        return

    try:
        dynamo_item = {}
        for key, value in summary.items():
            if value is None:
                continue
            if isinstance(value, float):
                dynamo_item[key] = Decimal(str(value))
            elif isinstance(value, int) and not isinstance(value, bool):
                dynamo_item[key] = Decimal(str(value))
            else:
                dynamo_item[key] = value

        _log_table.put_item(Item=dynamo_item)
        logger.info(
            "📊 [DB 요약] session=%s clear=%s score=%s",
            session_id[:8],
            is_game_clear,
            final_score,
        )
    except Exception as exc:
        # 분석 로그 적재 실패가 게임 진행을 막아서는 안 되므로 모든 예외를 흡수합니다.
        logger.error("세션 요약 로그 기록 실패 (게임 진행에는 영향 없음): %s", exc)


def get_local_logs() -> list[dict]:
    """로컬 개발용 인메모리 로그를 반환합니다 (디버깅/분석용)."""
    return _local_logs.copy()


def _to_native(value: Any) -> Any:
    """Decimal → int/float 로 재귀 변환 (JSON 직렬화 가능하게)."""
    if isinstance(value, Decimal):
        return int(value) if value == value.to_integral_value() else float(value)
    if isinstance(value, list):
        return [_to_native(v) for v in value]
    if isinstance(value, dict):
        return {k: _to_native(v) for k, v in value.items()}
    return value


def list_all_logs() -> list[dict]:
    """관리자용 — 전체 로그 목록을 JSON 직렬화 가능한 형태로 반환."""
    raw = _scan_all_logs() if _is_available else _local_logs
    return [_to_native(item) for item in raw]


def _to_int(value: Any) -> int:
    """Decimal·str·int 등 다양한 타입을 안전하게 int 로 변환합니다 (실패 시 0)."""
    if value is None:
        return 0
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def get_analytics_summary() -> dict[str, Any]:
    """
    레벨별 취약도 분석 요약을 반환합니다.

    "어떤 심사 항목에 사람들이 취약한지"를 파악할 수 있도록, 각 레벨에 대해
    세션 단위 통과율, 클리어까지 평균 시도 횟수, 가장 자주 누락된 통과 기준
    (weak_criteria)을 계산합니다.

    주의: pass_rate(메시지 단위 통과 비율)와 달리 clear_rate 는 세션 단위
    지표입니다. 한 레벨에서 여러 번 실패 후 통과해도 클리어로 집계됩니다.
    """
    logs = _local_logs if not _is_available else _scan_all_logs()

    if not logs:
        return {
            "total_sessions": 0,
            "total_interactions": 0,
            "clear_rate": 0,
            "levels": {},
        }

    # 채팅 로그와 세션 요약 분리
    chat_logs = [l for l in logs if l.get("log_id") != "SUMMARY"]
    summaries = [l for l in logs if l.get("log_id") == "SUMMARY"]

    level_stats: dict[int, dict] = {}
    for level in (1, 2, 3):
        level_logs = [l for l in chat_logs if _to_int(l.get("level")) == level]
        if not level_logs:
            continue

        # 세션 단위 지표: 이 레벨에 '도달'한 세션과 '클리어'한 세션
        reached_sessions = {l.get("session_id") for l in level_logs}
        clear_logs = [l for l in level_logs if l.get("is_level_clear")]
        cleared_sessions = {l.get("session_id") for l in clear_logs}

        # 클리어한 세션들이 클리어 시점까지 사용한 시도 횟수의 평균
        attempts = [_to_int(l.get("level_attempt")) for l in clear_logs]
        attempts = [a for a in attempts if a > 0]
        avg_attempts = round(sum(attempts) / len(attempts), 2) if attempts else None

        # 불합격 로그에서 누락된 통과 기준 번호의 빈도를 집계
        fail_logs = [l for l in level_logs if l.get("ai_status") == "fail"]
        criteria_counter: dict[int, int] = {}
        for log in fail_logs:
            for raw_idx in (log.get("missing_criteria") or []):
                idx = _to_int(raw_idx)
                if idx > 0:
                    criteria_counter[idx] = criteria_counter.get(idx, 0) + 1

        # 동적 설정의 현재 통과 기준을 사용 (관리자 수정이 반영되도록)
        level_cfg = config_service.get_level_config(level) or LEVEL_CONFIGS.get(level, {})
        pass_criteria = level_cfg.get("pass_criteria", [])
        weak_criteria = [
            {
                "index": idx,
                "criterion": (
                    pass_criteria[idx - 1]
                    if 1 <= idx <= len(pass_criteria)
                    else f"기준 {idx}"
                ),
                "fail_count": count,
            }
            for idx, count in sorted(
                criteria_counter.items(), key=lambda x: x[1], reverse=True
            )
        ]

        level_stats[level] = {
            "domain": level_logs[0].get("domain", ""),
            "reached_sessions": len(reached_sessions),
            "cleared_sessions": len(cleared_sessions),
            "clear_rate": (
                round(len(cleared_sessions) / len(reached_sessions) * 100, 1)
                if reached_sessions
                else 0
            ),
            "avg_attempts_to_clear": avg_attempts,
            "total_messages": len(level_logs),
            "fail_messages": len(fail_logs),
            "weak_criteria": weak_criteria,
        }

    cleared_games = sum(1 for s in summaries if s.get("is_game_clear"))
    return {
        "total_sessions": len(summaries),
        "total_interactions": len(chat_logs),
        "clear_rate": (
            round(cleared_games / len(summaries) * 100, 1) if summaries else 0
        ),
        "levels": level_stats,
    }


def _scan_all_logs() -> list[dict]:
    """DynamoDB에서 전체 로그를 스캔합니다."""
    if not _is_available or _log_table is None:
        return []

    try:
        response = _log_table.scan()
        items = response.get("Items", [])

        # 페이지네이션 처리
        while "LastEvaluatedKey" in response:
            response = _log_table.scan(
                ExclusiveStartKey=response["LastEvaluatedKey"]
            )
            items.extend(response.get("Items", []))

        return items
    except ClientError as exc:
        logger.error("로그 스캔 실패: %s", exc)
        return []
