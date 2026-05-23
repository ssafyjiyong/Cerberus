"""
Cerberus: The Dark Auditor - DynamoDB 리더보드 서비스

리더보드 데이터의 조회, 등록, 테이블 관리를 담당합니다.
DynamoDB를 사용할 수 없는 로컬 개발 환경에서는 목업 데이터를 반환합니다.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

import boto3
from botocore.exceptions import ClientError

from config import AWS_REGION, DYNAMODB_TABLE_NAME
from models import LeaderboardEntry

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# DynamoDB 리소스 초기화
# ──────────────────────────────────────────────
_dynamodb = None
_table = None
_is_available = False

try:
    _dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
    _table = _dynamodb.Table(DYNAMODB_TABLE_NAME)
    # 테이블 존재 확인을 위한 간단한 describe 호출
    _table.load()
    _is_available = True
    logger.info(
        "DynamoDB 테이블 '%s' 연결 성공 (리전: %s)",
        DYNAMODB_TABLE_NAME,
        AWS_REGION,
    )
except Exception as exc:
    logger.warning(
        "DynamoDB를 사용할 수 없습니다 (로컬 개발 모드): %s", exc
    )
    _is_available = False


# ──────────────────────────────────────────────
# 목업 데이터 (로컬 개발용)
# ──────────────────────────────────────────────
_MOCK_LEADERBOARD: list[dict] = [
    {"rank": 1, "name": "SecurityMaster", "score": 280, "time_used": 120.5, "created_at": "2026-01-15T09:00:00Z"},
    {"rank": 2, "name": "CyberGuard", "score": 265, "time_used": 135.2, "created_at": "2026-01-14T14:30:00Z"},
    {"rank": 3, "name": "ISMSPro", "score": 250, "time_used": 150.0, "created_at": "2026-01-13T11:20:00Z"},
    {"rank": 4, "name": "AuditAce", "score": 240, "time_used": 160.8, "created_at": "2026-01-12T16:45:00Z"},
    {"rank": 5, "name": "FirewallKing", "score": 230, "time_used": 170.3, "created_at": "2026-01-11T10:15:00Z"},
]


def ensure_table_exists() -> None:
    """
    DynamoDB 리더보드 테이블이 존재하지 않으면 생성합니다 (앱 시작 시 호출).

    테이블 스키마:
    - Partition Key: id (S)
    - GSI: score-index on score (N) for descending sort
    """
    global _table, _is_available

    if _dynamodb is None:
        logger.warning("DynamoDB 리소스가 초기화되지 않았습니다.")
        return

    try:
        _dynamodb.meta.client.describe_table(TableName=DYNAMODB_TABLE_NAME)
        logger.info("테이블 '%s'이(가) 이미 존재합니다.", DYNAMODB_TABLE_NAME)
    except ClientError as exc:
        if exc.response["Error"]["Code"] == "ResourceNotFoundException":
            logger.info("테이블 '%s' 생성 중...", DYNAMODB_TABLE_NAME)
            _table = _dynamodb.create_table(
                TableName=DYNAMODB_TABLE_NAME,
                KeySchema=[
                    {"AttributeName": "id", "KeyType": "HASH"},
                ],
                AttributeDefinitions=[
                    {"AttributeName": "id", "AttributeType": "S"},
                    {"AttributeName": "score", "AttributeType": "N"},
                    {"AttributeName": "created_at", "AttributeType": "S"},
                ],
                GlobalSecondaryIndexes=[
                    {
                        "IndexName": "score-index",
                        "KeySchema": [
                            {"AttributeName": "score", "KeyType": "HASH"},
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
                    "WriteCapacityUnits": 5,
                },
            )
            _table.wait_until_exists()
            _is_available = True
            logger.info("테이블 '%s' 생성 완료.", DYNAMODB_TABLE_NAME)
        else:
            logger.error("테이블 확인 중 오류: %s", exc)
            raise


def get_leaderboard() -> list[LeaderboardEntry]:
    """
    리더보드 상위 10명을 점수 내림차순으로 조회합니다.

    Returns:
        LeaderboardEntry 리스트 (최대 10개)
    """
    if not _is_available:
        logger.info("DynamoDB 미사용 → 목업 리더보드 데이터를 반환합니다.")
        return [LeaderboardEntry(**entry) for entry in _MOCK_LEADERBOARD]

    try:
        # 전체 스캔 후 정렬 (소규모 데이터에 적합)
        response = _table.scan()
        items = response.get("Items", [])

        # score 내림차순 정렬
        items.sort(key=lambda x: float(x.get("score", 0)), reverse=True)

        # 상위 10개만 선택하고 순위 부여
        top_items = items[:10]
        entries: list[LeaderboardEntry] = []
        for rank, item in enumerate(top_items, start=1):
            entries.append(
                LeaderboardEntry(
                    rank=rank,
                    name=str(item.get("name", "Unknown")),
                    score=int(item.get("score", 0)),
                    time_used=float(item.get("time_used", 0)),
                    created_at=str(item.get("created_at", "")),
                )
            )
        return entries

    except ClientError as exc:
        logger.error("리더보드 조회 실패: %s", exc)
        return [LeaderboardEntry(**entry) for entry in _MOCK_LEADERBOARD]


def submit_score(name: str, score: int, time_used: float) -> bool:
    """
    리더보드에 점수를 등록합니다.
    상위 10위 안에 들어야만 등록됩니다.

    Args:
        name: 플레이어 이름
        score: 최종 점수
        time_used: 소요 시간(초)

    Returns:
        True → 상위 10위 안에 등록됨 / False → 등록 실패 또는 순위 밖
    """
    if not _is_available:
        logger.info("DynamoDB 미사용 → 점수 등록을 시뮬레이션합니다.")
        # 목업: 항상 등록 성공으로 처리
        return True

    try:
        # 현재 리더보드 조회
        current = get_leaderboard()

        # 10개 미만이면 바로 등록, 10개 이상이면 최하위 점수와 비교
        if len(current) >= 10 and score <= current[-1].score:
            logger.info(
                "점수 %d는 상위 10위 밖입니다 (최소 %d).",
                score,
                current[-1].score,
            )
            return False

        # DynamoDB에 항목 추가
        item_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()

        _table.put_item(
            Item={
                "id": item_id,
                "name": name,
                "score": Decimal(str(score)),
                "time_used": Decimal(str(round(time_used, 2))),
                "created_at": now,
            }
        )

        logger.info(
            "리더보드 등록 성공: name=%s, score=%d, time=%.2f",
            name,
            score,
            time_used,
        )

        # 10위 초과 항목 정리
        _cleanup_leaderboard()

        return True

    except ClientError as exc:
        logger.error("점수 등록 실패: %s", exc)
        return False


def delete_leaderboard_entry(entry_id: str) -> bool:
    """관리자가 특정 리더보드 항목을 삭제합니다."""
    if not _is_available:
        # Mock 모드: id 가 없으므로 no-op
        logger.info("Mock 모드 — 리더보드 삭제 요청 무시 (id=%s)", entry_id)
        return True
    try:
        _table.delete_item(Key={"id": entry_id})
        logger.info("리더보드 항목 삭제: %s", entry_id)
        return True
    except ClientError as exc:
        logger.error("리더보드 항목 삭제 실패: %s", exc)
        return False


def clear_leaderboard() -> int:
    """관리자가 리더보드 전체를 초기화합니다. 삭제된 항목 수를 반환."""
    if not _is_available:
        count = len(_MOCK_LEADERBOARD)
        _MOCK_LEADERBOARD.clear()
        logger.info("Mock 리더보드 초기화 — %d개 항목 제거", count)
        return count
    try:
        response = _table.scan()
        items = response.get("Items", [])
        for item in items:
            try:
                _table.delete_item(Key={"id": item["id"]})
            except ClientError as exc:
                logger.warning("항목 삭제 중 오류: %s", exc)
        logger.info("리더보드 전체 초기화 — %d개 항목 제거", len(items))
        return len(items)
    except ClientError as exc:
        logger.error("리더보드 초기화 실패: %s", exc)
        return 0


def list_all_entries() -> list[dict]:
    """관리자용 — 리더보드 전체 항목을 id 포함하여 반환."""
    if not _is_available:
        return [dict(e) for e in _MOCK_LEADERBOARD]
    try:
        response = _table.scan()
        items = response.get("Items", [])
        # Decimal → 기본형 변환
        result = []
        for item in items:
            result.append(
                {
                    "id": str(item.get("id", "")),
                    "name": str(item.get("name", "")),
                    "score": int(item.get("score", 0)),
                    "time_used": float(item.get("time_used", 0)),
                    "created_at": str(item.get("created_at", "")),
                }
            )
        result.sort(key=lambda x: x["score"], reverse=True)
        return result
    except ClientError as exc:
        logger.error("리더보드 전체 조회 실패: %s", exc)
        return []


def _cleanup_leaderboard() -> None:
    """리더보드가 10개를 초과하면 하위 항목을 삭제합니다."""
    if not _is_available or _table is None:
        return

    try:
        response = _table.scan()
        items = response.get("Items", [])

        if len(items) <= 10:
            return

        # score 내림차순 정렬
        items.sort(key=lambda x: float(x.get("score", 0)), reverse=True)

        # 11위 이후 항목 삭제
        for item in items[10:]:
            _table.delete_item(Key={"id": item["id"]})
            logger.info("하위 항목 삭제: id=%s, score=%s", item["id"], item.get("score"))

    except ClientError as exc:
        logger.error("리더보드 정리 실패: %s", exc)
