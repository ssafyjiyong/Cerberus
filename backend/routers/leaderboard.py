"""
Cerberus: The Dark Auditor - 리더보드 라우터

리더보드 조회 및 점수 제출 API 엔드포인트를 정의합니다.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from models import LeaderboardEntry, LeaderboardSubmitRequest
from services import dynamo_service, game_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/leaderboard", tags=["리더보드"])


@router.get(
    "",
    response_model=list[LeaderboardEntry],
    summary="리더보드 조회",
    description="상위 10명의 리더보드를 점수 내림차순으로 반환합니다.",
)
async def get_leaderboard() -> list[LeaderboardEntry]:
    """
    리더보드 상위 10명을 조회합니다.

    Returns:
        LeaderboardEntry 리스트 (최대 10개)
    """
    try:
        return dynamo_service.get_leaderboard()
    except Exception as exc:
        logger.error("리더보드 조회 실패: %s", exc)
        raise HTTPException(
            status_code=500,
            detail="리더보드를 불러올 수 없습니다.",
        ) from exc


@router.post(
    "",
    summary="점수 제출",
    description="게임 클리어 후 리더보드에 점수를 등록합니다.",
)
async def submit_score(request: LeaderboardSubmitRequest) -> dict:
    """
    게임 클리어 세션의 점수를 리더보드에 등록합니다.

    Args:
        request: 세션 ID와 플레이어 이름이 포함된 요청

    Returns:
        등록 결과 메시지

    Raises:
        HTTPException: 세션이 없거나 게임을 클리어하지 않은 경우
    """
    # 세션 검증
    session = game_service.get_session(request.session_id)
    if session is None:
        raise HTTPException(
            status_code=404,
            detail="세션을 찾을 수 없습니다.",
        )

    if not session.is_completed or session.final_score is None:
        raise HTTPException(
            status_code=400,
            detail="게임을 클리어한 세션만 점수를 등록할 수 있습니다.",
        )

    # 점수 등록
    try:
        is_registered = dynamo_service.submit_score(
            name=request.name,
            score=session.final_score,
            time_used=session.time_used,
        )

        if is_registered:
            return {
                "success": True,
                "message": f"🎉 축하합니다! '{request.name}'님의 점수({session.final_score}점)가 리더보드에 등록되었습니다!",
                "score": session.final_score,
                "time_used": session.time_used,
            }
        else:
            return {
                "success": False,
                "message": "아쉽게도 상위 10위 안에 들지 못했습니다. 다음에 도전해 주세요!",
                "score": session.final_score,
                "time_used": session.time_used,
            }

    except Exception as exc:
        logger.error("점수 등록 실패: %s", exc)
        raise HTTPException(
            status_code=500,
            detail="점수 등록 중 오류가 발생했습니다.",
        ) from exc
