"""
Cerberus: The Dark Auditor - 게임 라우터

게임 시작 및 채팅 API 엔드포인트를 정의합니다.
각 단계는 독립 세션으로 운영되며, /start 호출 시 `level` 로 단계를 지정합니다.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from models import ChatRequest, ChatResponse, GameStartRequest, GameStartResponse
from services import config_service, game_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/game", tags=["게임"])


@router.post(
    "/start",
    response_model=GameStartResponse,
    summary="게임 시작 (단계 단위)",
    description=(
        "지정된 레벨의 새로운 게임 세션을 생성하고 해당 단계의 질문/한도를 반환합니다. "
        "각 단계는 독립 세션이므로 단계 전환 시마다 이 엔드포인트를 다시 호출하세요."
    ),
)
async def start_game(request: GameStartRequest | None = None) -> GameStartResponse:
    level = request.level if request else 1
    try:
        session = game_service.create_session(level=level)
        runtime = config_service.get_effective_level_runtime(level)

        return GameStartResponse(
            session_id=session.session_id,
            level=level,
            domain=runtime["domain"],
            question=runtime["question"],
            time_limit=session.time_limit,
            p_max=session.p_max,
            pass_logic=session.pass_logic,
            message=(
                f"🔥 STAGE {level} — ISMS 인증 심사가 시작되었습니다.\n"
                f"📋 심사 영역: {runtime['domain']}\n"
                "심사원의 질문에 성실히 답변해 주세요."
            ),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        if str(exc) == "MAINTENANCE_MODE":
            raise HTTPException(
                status_code=503,
                detail="현재 점검 중입니다. 잠시 후 다시 시도해 주세요.",
            ) from exc
        logger.error("게임 시작 실패: %s", exc)
        raise HTTPException(
            status_code=500,
            detail="게임 세션 생성에 실패했습니다. 잠시 후 다시 시도해 주세요.",
        ) from exc
    except Exception as exc:
        logger.error("게임 시작 실패: %s", exc)
        raise HTTPException(
            status_code=500,
            detail="게임 세션 생성에 실패했습니다. 잠시 후 다시 시도해 주세요.",
        ) from exc


@router.post(
    "/chat",
    response_model=ChatResponse,
    summary="채팅 메시지 전송",
    description="사용자의 답변 메시지를 AI 심사원에게 전달하고 평가 결과를 반환합니다.",
)
async def chat(request: ChatRequest) -> ChatResponse:
    try:
        response = game_service.process_chat(
            session_id=request.session_id,
            message=request.message,
        )
        return response
    except ValueError as exc:
        logger.warning("채팅 처리 실패 (잘못된 요청): %s", exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("채팅 처리 중 서버 오류: %s", exc)
        raise HTTPException(
            status_code=500,
            detail="채팅 처리 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.",
        ) from exc
