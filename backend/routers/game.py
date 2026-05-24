"""
Cerberus: The Dark Auditor - 게임 라우터

게임 시작 및 채팅 API 엔드포인트를 정의합니다.
각 단계는 독립 세션으로 운영되며, /start 호출 시 `level` 로 단계를 지정합니다.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from models import ChatRequest, ChatResponse, GameStartRequest, GameStartResponse
from services import game_service


def _build_exemplar_payload(session) -> dict:
    """세션 스냅샷 질문에서 학습용으로 안전하게 노출할 정보만 추립니다."""
    q = session.question or {}
    paths = []
    for p in q.get("answer_paths", []) or []:
        paths.append(
            {
                "id": p.get("id", ""),
                "tier": p.get("tier", ""),
                "description": p.get("description", ""),
                "trigger_keywords": p.get("trigger_keywords", []),
                "rebuttal": p.get("rebuttal", ""),
                "follow_up": p.get("follow_up", ""),
                "acknowledgment_keywords": p.get("acknowledgment_keywords", []),
                "compensating_keywords": p.get("compensating_keywords", []),
                "exemplar_answer": p.get("exemplar_answer", ""),
            }
        )
    return {
        "session_id": session.session_id,
        "level": session.level,
        "is_cleared": session.is_cleared,
        "final_tier": session.final_tier,
        "final_score": session.final_score,
        "isms_control_id": q.get("isms_control_id", ""),
        "isms_control_title": q.get("isms_control_title", ""),
        "scenario_context": q.get("scenario_context", ""),
        "auditor_question": q.get("auditor_question", ""),
        "default_rebuttal": q.get("default_rebuttal", ""),
        "answer_paths": paths,
    }

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
        q = session.question or {}
        return GameStartResponse(
            session_id=session.session_id,
            level=level,
            title=session.title or f"STAGE {level}",
            subtitle=session.subtitle,
            domain=session.subtitle,  # legacy 호환
            isms_control_id=q.get("isms_control_id", ""),
            isms_control_title=q.get("isms_control_title", ""),
            scenario_context=q.get("scenario_context", ""),
            question=q.get("auditor_question", ""),
            time_limit=session.time_limit,
            p_max=session.p_max,
            message=(
                f"🔥 STAGE {level} — {session.title or 'ISMS-P 심사'} 가 시작되었습니다.\n"
                f"📋 영역: {session.subtitle or '-'}\n"
                f"📑 근거 항목: {q.get('isms_control_id', '?')} {q.get('isms_control_title', '')}"
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


@router.get(
    "/session/{session_id}/exemplars",
    summary="모범답안 조회 (세션 종료 후)",
    description=(
        "세션이 종료된(is_completed=true) 경우에만 출제된 질문의 시나리오·"
        "answer_paths·모범답안을 학습용으로 노출합니다. 진행 중 세션은 403."
    ),
)
async def get_session_exemplars(session_id: str) -> dict:
    session = game_service.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")
    if not session.is_completed:
        raise HTTPException(
            status_code=403,
            detail="아직 진행 중인 세션의 모범답안은 조회할 수 없습니다.",
        )
    return _build_exemplar_payload(session)
