"""
Cerberus: The Dark Auditor - 게임 라우터

게임 시작 및 채팅 API 엔드포인트를 정의합니다.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from models import ChatRequest, ChatResponse, GameStartResponse
from prompts.auditor_prompt import LEVEL_CONFIGS
from services import game_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/game", tags=["게임"])


@router.post(
    "/start",
    response_model=GameStartResponse,
    summary="게임 시작",
    description="새로운 게임 세션을 생성하고 Level 1 심사 질문을 반환합니다.",
)
async def start_game() -> GameStartResponse:
    """
    새 게임 세션을 생성합니다.

    Returns:
        GameStartResponse: 세션 ID, 레벨, 첫 번째 질문, 안내 메시지
    """
    try:
        session = game_service.create_session()
        level_config = LEVEL_CONFIGS[1]

        return GameStartResponse(
            session_id=session.session_id,
            level=1,
            question=level_config["question"],
            message=(
                "🔥 ISMS 인증 심사가 시작되었습니다.\n"
                f"📋 심사 영역: {level_config['domain']}\n"
                "심사원의 질문에 성실히 답변해 주세요."
            ),
        )
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
    """
    사용자의 답변을 AI 심사원에게 전달하여 평가를 받습니다.

    Args:
        request: 세션 ID와 사용자 메시지가 포함된 요청

    Returns:
        ChatResponse: 평가 결과 (pass/fail), 피드백 메시지, 게임 상태
    """
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
