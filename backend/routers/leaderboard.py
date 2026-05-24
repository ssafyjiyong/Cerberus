"""
Cerberus: The Dark Auditor - 리더보드 라우터

리더보드 조회 및 점수 제출 API 엔드포인트를 정의합니다.
각 단계가 독립 세션이므로, 제출 시 모든 단계 세션 ID 를 함께 보내고
백엔드가 합산하여 등록합니다.
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
    summary="점수 제출 (모든 단계 합산)",
    description=(
        "모든 단계를 클리어한 세션 ID 목록을 받아, 점수와 소요 시간을 "
        "합산하여 리더보드에 등록합니다."
    ),
)
async def submit_score(request: LeaderboardSubmitRequest) -> dict:
    total_score = 0
    total_time = 0.0
    levels_seen: set[int] = set()

    for sid in request.session_ids:
        session = game_service.get_session(sid)
        if session is None:
            raise HTTPException(
                status_code=404,
                detail=f"세션을 찾을 수 없습니다: {sid[:8]}...",
            )
        if not session.is_completed or not session.is_cleared or session.final_score is None:
            raise HTTPException(
                status_code=400,
                detail=f"클리어하지 않은 세션이 포함되어 있습니다 (level={session.level}).",
            )
        if session.level in levels_seen:
            raise HTTPException(
                status_code=400,
                detail=f"동일 레벨의 세션이 중복되었습니다: level {session.level}",
            )
        levels_seen.add(session.level)
        total_score += int(session.final_score)
        total_time += float(session.time_used)

    if levels_seen != {1, 2, 3}:
        missing = sorted({1, 2, 3} - levels_seen)
        raise HTTPException(
            status_code=400,
            detail=f"모든 단계(1·2·3)를 클리어해야 등록할 수 있습니다. 누락: {missing}",
        )

    try:
        is_registered = dynamo_service.submit_score(
            name=request.name,
            score=total_score,
            time_used=total_time,
        )
        if is_registered:
            return {
                "success": True,
                "message": (
                    f"🎉 축하합니다! '{request.name}'님의 점수({total_score}점)가 "
                    "리더보드에 등록되었습니다!"
                ),
                "score": total_score,
                "time_used": total_time,
            }
        return {
            "success": False,
            "message": "아쉽게도 상위 10위 안에 들지 못했습니다. 다음에 도전해 주세요!",
            "score": total_score,
            "time_used": total_time,
        }
    except Exception as exc:
        logger.error("점수 등록 실패: %s", exc)
        raise HTTPException(
            status_code=500,
            detail="점수 등록 중 오류가 발생했습니다.",
        ) from exc
