"""
Cerberus: The Dark Auditor - 리더보드 라우터

리더보드 조회 및 점수 제출 API 엔드포인트를 정의합니다.
각 단계가 독립 세션이므로, 제출 시 클리어한 단계의 세션 ID 를 함께 보내고
백엔드가 합산하여 등록합니다.

등록 조건 (v2):
  - 클리어한 단계가 1개 이상이고 누적 점수가 1점 이상이면 등록 가능.
    (게임오버여도 일부 단계만 클리어했다면 그 점수로 등록 가능)
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
    summary="점수 제출 (클리어한 단계 합산)",
    description=(
        "클리어한 단계의 세션 ID 목록을 받아 점수와 소요 시간을 합산해 등록합니다. "
        "전체 3단계를 모두 클리어하지 않았어도, 1점 이상 누적이면 등록 가능합니다."
    ),
)
async def submit_score(request: LeaderboardSubmitRequest) -> dict:
    total_score = 0
    total_time = 0.0
    levels_seen: set[int] = set()
    accepted_levels: list[int] = []

    for sid in request.session_ids:
        session = game_service.get_session(sid)
        if session is None:
            # 존재하지 않는 세션은 조용히 무시 (게임오버 시 미클리어 세션 포함될 수 있음)
            logger.info("submit_score: 세션 미존재로 건너뜀: %s", sid[:8] if sid else "")
            continue
        if not session.is_completed or not session.is_cleared or session.final_score is None:
            # 클리어하지 않은 세션도 무시 (시간/시도 초과로 끝난 세션 등)
            continue
        if session.level in levels_seen:
            raise HTTPException(
                status_code=400,
                detail=f"동일 레벨의 세션이 중복되었습니다: level {session.level}",
            )
        levels_seen.add(session.level)
        accepted_levels.append(session.level)
        total_score += int(session.final_score)
        total_time += float(session.time_used)

    if total_score < 1 or not accepted_levels:
        raise HTTPException(
            status_code=400,
            detail="등록 가능한 점수가 없습니다. 최소 한 단계 이상 클리어해야 합니다.",
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
                "cleared_levels": sorted(accepted_levels),
            }
        return {
            "success": False,
            "message": "아쉽게도 상위 10위 안에 들지 못했습니다. 다음에 도전해 주세요!",
            "score": total_score,
            "time_used": total_time,
            "cleared_levels": sorted(accepted_levels),
        }
    except Exception as exc:
        logger.error("점수 등록 실패: %s", exc)
        raise HTTPException(
            status_code=500,
            detail="점수 등록 중 오류가 발생했습니다.",
        ) from exc
