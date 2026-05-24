"""
Cerberus — 시간 유틸리티

모든 백엔드 timestamp 는 KST(Asia/Seoul, UTC+9) 기준으로 통일합니다.
ISO 8601 직렬화 시 항상 `+09:00` 오프셋이 포함됩니다.
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta

# Asia/Seoul 은 표준 시간만 사용 (DST 없음) — 단순 fixed offset 으로 표현해도 정확합니다.
KST = timezone(timedelta(hours=9), name="KST")


def now_kst() -> datetime:
    """현재 시각을 KST(+09:00) datetime 으로 반환."""
    return datetime.now(tz=KST)


def now_kst_iso() -> str:
    """현재 시각을 ISO 8601 (KST, +09:00) 문자열로 반환."""
    return now_kst().isoformat()


def to_kst_iso(epoch_seconds: float) -> str:
    """epoch 초를 KST ISO 8601 문자열로 변환."""
    return datetime.fromtimestamp(epoch_seconds, tz=KST).isoformat()
