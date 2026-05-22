"""
Cerberus: The Dark Auditor - 분석 데이터 라우터

게임 로그 분석 데이터를 조회하는 API 엔드포인트입니다.
추후 관리자 대시보드 등에서 활용할 수 있습니다.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter

from services import analytics_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/analytics", tags=["분석"])


@router.get(
    "/summary",
    summary="분석 요약 조회",
    description="레벨별 통과율, 총 세션 수 등 분석 데이터 요약을 반환합니다.",
)
async def get_analytics_summary() -> dict:
    """
    게임 분석 요약을 반환합니다.

    Returns:
        레벨별 통과율, 총 세션 수, 총 상호작용 수 등
    """
    try:
        return analytics_service.get_analytics_summary()
    except Exception as exc:
        logger.error("분석 데이터 조회 실패: %s", exc)
        return {"error": str(exc), "total_sessions": 0, "levels": {}}


@router.get(
    "/logs",
    summary="게임 로그 조회 (개발용)",
    description="로컬 개발 환경에서 인메모리 게임 로그를 조회합니다.",
)
async def get_game_logs() -> dict:
    """
    로컬 개발용 인메모리 로그를 반환합니다.

    Returns:
        로그 목록 및 총 개수
    """
    logs = analytics_service.get_local_logs()
    return {
        "total": len(logs),
        "logs": logs[-50:],  # 최근 50건만 반환
    }
