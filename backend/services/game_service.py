"""
Cerberus: The Dark Auditor - 게임 서비스

게임 세션 관리, 채팅 처리, 점수 계산 등 핵심 게임 로직을 담당합니다.
세션은 인메모리 딕셔너리로 관리됩니다.

설계 (v2)
─────
각 단계(Level 1·2·3)는 **독립된 세션** 으로 운영됩니다. 세션 생성 시 해당
스테이지의 질문 풀에서 무작위로 1문제가 출제되어 세션에 스냅샷됩니다.

평가는 시나리오 기반 answer_paths 에 의해 tier(full/half/fail)로 분류되며:
  - full → 단계 통과 + 만점
  - half → 단계 통과 + 만점의 50%
  - fail → 같은 세션 계속 (p_max 까지)

리더보드는 클리어한 단계가 1개 이상이고 누적 점수가 1점 이상이면 등록 가능합니다.
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from models import ChatResponse
from prompts.auditor_prompt import normalize_tier
from services import analytics_service, bedrock_service, config_service

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# 게임 세션 데이터 클래스 (단계 단위)
# ──────────────────────────────────────────────

@dataclass
class GameSession:
    """단일 단계의 게임 세션 상태."""

    session_id: str
    level: int = 1
    conversation_history: list[dict] = field(default_factory=list)
    prompt_count: int = 0
    start_time: float = field(default_factory=time.time)
    is_completed: bool = False     # 세션 종료 (full/half/fail/timeout/limit 어떤 이유든)
    is_cleared: bool = False        # 통과 여부 (full 또는 half)
    final_score: Optional[int] = None
    final_tier: Optional[str] = None  # "full" | "half"
    end_reason: Optional[str] = None  # "clear" | "timeout" | "prompt_limit" | "error"

    # 세션 생성 시점의 파라미터 스냅샷 (관리자가 중간에 바꿔도 영향 없음)
    title: str = ""
    subtitle: str = ""
    base_score: int = 1000
    question: dict = field(default_factory=dict)
    time_limit: int = 300
    p_max: int = 10
    w_time: int = 1
    w_prompt: int = 10

    @property
    def time_used(self) -> float:
        return round(time.time() - self.start_time, 2)

    @property
    def is_time_over(self) -> bool:
        return self.time_used >= self.time_limit

    @property
    def is_prompt_over(self) -> bool:
        return self.prompt_count >= self.p_max


# ──────────────────────────────────────────────
# 인메모리 세션 저장소
# ──────────────────────────────────────────────
_sessions: dict[str, GameSession] = {}


def create_session(level: int = 1) -> GameSession:
    """
    새로운 게임 세션을 생성합니다 (단일 단계용).

    질문 풀에서 무작위로 1문제가 선택되어 세션 시작 시점에 스냅샷됩니다.

    Raises:
        RuntimeError("MAINTENANCE_MODE"): 관리자가 유지보수 모드를 켠 상태일 때.
        ValueError: 유효하지 않은 레벨.
    """
    if config_service.is_maintenance_mode():
        raise RuntimeError("MAINTENANCE_MODE")
    if level not in (1, 2, 3):
        raise ValueError(f"유효하지 않은 레벨입니다: {level}")

    runtime = config_service.get_effective_stage_runtime(level)
    params = config_service.get_game_params()

    session_id = str(uuid.uuid4())
    session = GameSession(
        session_id=session_id,
        level=level,
        title=runtime["title"],
        subtitle=runtime["subtitle"],
        base_score=int(runtime["base_score"]),
        question=runtime["question"],
        time_limit=int(runtime["time_limit"]),
        p_max=int(runtime["p_max"]),
        w_time=int(params.get("W_TIME", 1)),
        w_prompt=int(params.get("W_PROMPT", 10)),
    )
    _sessions[session_id] = session
    logger.info(
        "새 게임 세션 생성: %s (level=%d, q_id=%s, p_max=%d, time_limit=%d)",
        session_id, level, session.question.get("id"), session.p_max, session.time_limit,
    )
    return session


def get_session(session_id: str) -> Optional[GameSession]:
    """세션 ID 로 기존 게임 세션을 조회합니다."""
    return _sessions.get(session_id)


def _finalize_failure(session: GameSession, reason: str, message: str) -> ChatResponse:
    """타임아웃 / 프롬프트 한도 초과 등 실패 종료 공통 처리."""
    session.is_completed = True
    session.is_cleared = False
    session.end_reason = reason
    analytics_service.log_game_session_summary(
        session_id=session.session_id,
        final_level=session.level,
        is_completed=True,
        is_game_clear=False,
        total_prompts=session.prompt_count,
        total_time=session.time_used,
        end_reason=reason,
    )
    return ChatResponse(
        status="fail",
        tier="fail",
        matched_path_id="",
        message=message,
        level=session.level,
        is_stage_clear=False,
        score=None,
        prompt_count=session.prompt_count,
        time_used=session.time_used,
    )


def _calculate_stage_score(session: GameSession, tier: str) -> int:
    """
    단계 점수 계산.

    공식 (full 기준):
        base = session.base_score
        time_bonus   = (time_limit - time_used) * w_time
        prompt_bonus = (p_max - prompt_count) * w_prompt
        full = base + time_bonus + prompt_bonus
        half = round(full * 0.5)
    """
    time_bonus = (session.time_limit - session.time_used) * session.w_time
    prompt_bonus = (session.p_max - session.prompt_count) * session.w_prompt
    full_score = session.base_score + time_bonus + prompt_bonus
    full_score = max(int(full_score), 0)
    if tier == "half":
        return max(int(round(full_score * 0.5)), 1)
    return full_score


def process_chat(session_id: str, message: str) -> ChatResponse:
    """
    사용자의 채팅 메시지를 처리하고 AI 심사원의 평가 결과를 반환합니다.
    tier ∈ {full, half, fail}.
    """
    session = get_session(session_id)
    if session is None:
        raise ValueError("세션을 찾을 수 없습니다. 새 게임을 시작해 주세요.")

    if session.is_completed:
        raise ValueError("이미 종료된 게임 세션입니다.")

    # ── 제한 시간 초과 ──
    if session.is_time_over:
        return _finalize_failure(
            session,
            "timeout",
            f"⏰ 제한 시간({session.time_limit}초)이 초과되었습니다. 게임 오버!",
        )

    # ── 프롬프트 횟수 초과 ──
    if session.is_prompt_over:
        return _finalize_failure(
            session,
            "prompt_limit",
            f"📝 최대 프롬프트 횟수({session.p_max}회)를 초과했습니다. 게임 오버!",
        )

    # ── 프롬프트 카운트 증가, 대화 이력 추가 ──
    session.prompt_count += 1
    session.conversation_history.append({"role": "user", "content": message})

    # ── Bedrock AI 평가 호출 ──
    try:
        result = bedrock_service.evaluate_answer(
            question=session.question,
            conversation_history=session.conversation_history,
        )
    except RuntimeError as exc:
        logger.error("Bedrock 호출 실패: %s", exc)
        # 롤백
        session.prompt_count -= 1
        session.conversation_history.pop()
        return ChatResponse(
            status="fail",
            tier="fail",
            matched_path_id="",
            message=f"심사원과의 통신 중 오류가 발생했습니다: {exc}",
            level=session.level,
            is_stage_clear=False,
            score=None,
            prompt_count=session.prompt_count,
            time_used=session.time_used,
        )

    session.conversation_history.append({"role": "assistant", "content": result["message"]})

    tier = normalize_tier(result.get("tier"))
    ai_message = result["message"]
    matched_id = result.get("matched_path_id", "")
    missing_aspects = result.get("missing_aspects", [])

    # ── 통과(full 또는 half) — 이 단계 종료 + 점수 계산 ──
    if tier in ("full", "half"):
        session.is_completed = True
        session.is_cleared = True
        session.final_tier = tier
        session.end_reason = "clear"
        score = _calculate_stage_score(session, tier)
        session.final_score = score

        analytics_service.log_chat_interaction(
            session_id=session.session_id,
            level=session.level,
            domain=session.subtitle or session.title,
            user_message=message,
            ai_status=tier,  # full | half
            ai_message=ai_message,
            prompt_count=session.prompt_count,
            time_used=session.time_used,
            level_attempt=session.prompt_count,
            missing_criteria=[],  # 통과이므로 누락 없음
            is_level_clear=True,
            is_game_clear=(session.level == 3 and tier == "full"),
        )
        analytics_service.log_game_session_summary(
            session_id=session.session_id,
            final_level=session.level,
            is_completed=True,
            is_game_clear=(session.level == 3),
            total_prompts=session.prompt_count,
            total_time=session.time_used,
            final_score=score,
            end_reason="clear",
        )

        tier_label = "만점 통과" if tier == "full" else "절반 점수 통과"
        return ChatResponse(
            status="pass",
            tier=tier,
            matched_path_id=matched_id,
            message=(
                f"✅ Level {session.level} {tier_label}!\n\n{ai_message}\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🏆 단계 점수: {score}점 ({tier})\n"
                f"⏱ 소요 시간: {session.time_used:.1f}초\n"
                f"📝 사용 프롬프트: {session.prompt_count}회"
            ),
            level=session.level,
            is_stage_clear=True,
            score=score,
            prompt_count=session.prompt_count,
            time_used=session.time_used,
        )

    # ── 불합격(fail) — 세션 계속 진행 ──
    analytics_service.log_chat_interaction(
        session_id=session.session_id,
        level=session.level,
        domain=session.subtitle or session.title,
        user_message=message,
        ai_status="fail",
        ai_message=ai_message,
        prompt_count=session.prompt_count,
        time_used=session.time_used,
        level_attempt=session.prompt_count,
        missing_criteria=[],  # legacy 필드 — 새 모델에선 missing_aspects 사용
        is_level_clear=False,
        is_game_clear=False,
    )

    return ChatResponse(
        status="fail",
        tier="fail",
        matched_path_id="",
        message=ai_message,
        level=session.level,
        is_stage_clear=False,
        score=None,
        prompt_count=session.prompt_count,
        time_used=session.time_used,
    )


def get_active_sessions() -> list[dict[str, Any]]:
    """
    현재 활성 상태인 게임 세션 목록을 반환합니다 (관리자 모니터링용).
    완료되었거나 시간 초과된 세션은 제외합니다.
    """
    active: list[dict[str, Any]] = []
    for sid, session in _sessions.items():
        if session.is_completed or session.is_time_over:
            continue
        active.append(
            {
                "session_id": sid,
                "current_level": session.level,
                "prompt_count": session.prompt_count,
                "time_used": session.time_used,
                "time_limit": session.time_limit,
                "started_at": time.strftime(
                    "%Y-%m-%dT%H:%M:%SZ", time.gmtime(session.start_time)
                ),
            }
        )
    active.sort(key=lambda s: s["started_at"], reverse=True)
    return active
