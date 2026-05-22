"""
Cerberus: The Dark Auditor - 게임 서비스

게임 세션 관리, 채팅 처리, 점수 계산 등 핵심 게임 로직을 담당합니다.
세션은 인메모리 딕셔너리로 관리됩니다.
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Optional

from config import P_MAX, TIME_LIMIT, W_PROMPT, W_TIME
from models import ChatResponse
from prompts.auditor_prompt import LEVEL_CONFIGS
from services import bedrock_service, analytics_service

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# 게임 세션 데이터 클래스
# ──────────────────────────────────────────────

@dataclass
class GameSession:
    """단일 게임 세션의 상태를 추적하는 데이터 클래스"""

    session_id: str
    current_level: int = 1
    conversation_histories: dict[int, list[dict]] = field(default_factory=dict)
    prompt_count: int = 0
    level_attempts: dict[int, int] = field(default_factory=dict)
    start_time: float = field(default_factory=time.time)
    is_completed: bool = False
    final_score: Optional[int] = None

    def __post_init__(self) -> None:
        """각 레벨의 대화 이력과 시도 횟수를 초기화합니다."""
        for level in LEVEL_CONFIGS:
            self.conversation_histories.setdefault(level, [])
            self.level_attempts.setdefault(level, 0)

    @property
    def time_used(self) -> float:
        """경과 시간(초)을 반환합니다."""
        return round(time.time() - self.start_time, 2)

    @property
    def is_time_over(self) -> bool:
        """제한 시간 초과 여부를 반환합니다."""
        return self.time_used >= TIME_LIMIT

    @property
    def is_prompt_over(self) -> bool:
        """프롬프트 횟수 초과 여부를 반환합니다."""
        return self.prompt_count >= P_MAX


# ──────────────────────────────────────────────
# 인메모리 세션 저장소
# ──────────────────────────────────────────────
_sessions: dict[str, GameSession] = {}


def create_session() -> GameSession:
    """
    새로운 게임 세션을 생성합니다.

    Returns:
        생성된 GameSession 인스턴스
    """
    session_id = str(uuid.uuid4())
    session = GameSession(session_id=session_id)
    _sessions[session_id] = session
    logger.info("새 게임 세션 생성: %s", session_id)
    return session


def get_session(session_id: str) -> Optional[GameSession]:
    """
    세션 ID로 기존 게임 세션을 조회합니다.

    Args:
        session_id: 조회할 세션 식별자

    Returns:
        GameSession 인스턴스 또는 None
    """
    return _sessions.get(session_id)


def process_chat(session_id: str, message: str) -> ChatResponse:
    """
    사용자의 채팅 메시지를 처리하고 AI 심사원의 평가 결과를 반환합니다.

    Args:
        session_id: 세션 식별자
        message: 사용자가 입력한 답변 메시지

    Returns:
        ChatResponse 모델 인스턴스

    Raises:
        ValueError: 세션을 찾을 수 없거나 이미 종료된 경우
    """
    session = get_session(session_id)
    if session is None:
        raise ValueError("세션을 찾을 수 없습니다. 새 게임을 시작해 주세요.")

    if session.is_completed:
        raise ValueError("이미 종료된 게임 세션입니다.")

    # ── 제한 시간 초과 확인 ──
    if session.is_time_over:
        session.is_completed = True
        # 📝 분석 로그: 타임아웃
        analytics_service.log_game_session_summary(
            session_id=session.session_id,
            final_level=session.current_level,
            is_completed=True,
            is_game_clear=False,
            total_prompts=session.prompt_count,
            total_time=session.time_used,
            end_reason="timeout",
        )
        return ChatResponse(
            status="fail",
            message=f"⏰ 제한 시간({TIME_LIMIT}초)이 초과되었습니다. 게임 오버!",
            level=session.current_level,
            is_game_clear=False,
            score=None,
            prompt_count=session.prompt_count,
            time_used=session.time_used,
        )

    # ── 프롬프트 횟수 초과 확인 ──
    if session.is_prompt_over:
        session.is_completed = True
        # 📝 분석 로그: 프롬프트 초과
        analytics_service.log_game_session_summary(
            session_id=session.session_id,
            final_level=session.current_level,
            is_completed=True,
            is_game_clear=False,
            total_prompts=session.prompt_count,
            total_time=session.time_used,
            end_reason="prompt_limit",
        )
        return ChatResponse(
            status="fail",
            message=f"📝 최대 프롬프트 횟수({P_MAX}회)를 초과했습니다. 게임 오버!",
            level=session.current_level,
            is_game_clear=False,
            score=None,
            prompt_count=session.prompt_count,
            time_used=session.time_used,
        )

    # ── 프롬프트 카운트 & 레벨별 시도 횟수 증가, 대화 이력 추가 ──
    session.prompt_count += 1
    session.level_attempts[session.current_level] += 1
    current_history = session.conversation_histories[session.current_level]
    current_history.append({"role": "user", "content": message})

    # ── Bedrock AI 평가 호출 ──
    try:
        result = bedrock_service.evaluate_answer(
            level=session.current_level,
            conversation_history=current_history,
        )
    except RuntimeError as exc:
        logger.error("Bedrock 호출 실패: %s", exc)
        # 프롬프트 카운트 & 레벨별 시도 횟수 롤백
        session.prompt_count -= 1
        session.level_attempts[session.current_level] -= 1
        current_history.pop()
        return ChatResponse(
            status="fail",
            message=f"심사원과의 통신 중 오류가 발생했습니다: {exc}",
            level=session.current_level,
            is_game_clear=False,
            score=None,
            prompt_count=session.prompt_count,
            time_used=session.time_used,
        )

    # ── AI 응답을 대화 이력에 추가 ──
    current_history.append({"role": "assistant", "content": result["message"]})

    status = result["status"]
    ai_message = result["message"]
    missing_criteria = result.get("missing_criteria", [])
    current_config = LEVEL_CONFIGS[session.current_level]

    # ── 통과(pass) 처리 ──
    if status == "pass":
        if session.current_level < 3:
            # 다음 레벨로 진행
            cleared_level = session.current_level
            next_level = session.current_level + 1
            session.current_level = next_level
            next_config = LEVEL_CONFIGS[next_level]

            # 📝 분석 로그: 레벨 클리어
            analytics_service.log_chat_interaction(
                session_id=session.session_id,
                level=cleared_level,
                domain=current_config["domain"],
                user_message=message,
                ai_status=status,
                ai_message=ai_message,
                prompt_count=session.prompt_count,
                time_used=session.time_used,
                level_attempt=session.level_attempts[cleared_level],
                missing_criteria=missing_criteria,
                is_level_clear=True,
                is_game_clear=False,
            )

            return ChatResponse(
                status="pass",
                message=(
                    f"✅ Level {next_level - 1} 통과!\n\n"
                    f"{ai_message}\n\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"📋 다음 심사 영역: {next_config['domain']}\n"
                    f"❓ {next_config['question']}"
                ),
                level=next_level,
                is_game_clear=False,
                score=None,
                prompt_count=session.prompt_count,
                time_used=session.time_used,
            )
        else:
            # 게임 클리어!
            session.is_completed = True
            score = calculate_score(session.time_used, session.prompt_count)
            session.final_score = score

            # 📝 분석 로그: 게임 클리어
            analytics_service.log_chat_interaction(
                session_id=session.session_id,
                level=session.current_level,
                domain=current_config["domain"],
                user_message=message,
                ai_status=status,
                ai_message=ai_message,
                prompt_count=session.prompt_count,
                time_used=session.time_used,
                level_attempt=session.level_attempts[session.current_level],
                missing_criteria=missing_criteria,
                is_level_clear=True,
                is_game_clear=True,
            )
            analytics_service.log_game_session_summary(
                session_id=session.session_id,
                final_level=session.current_level,
                is_completed=True,
                is_game_clear=True,
                total_prompts=session.prompt_count,
                total_time=session.time_used,
                final_score=score,
                end_reason="clear",
            )

            return ChatResponse(
                status="pass",
                message=(
                    f"🎉 축하합니다! 모든 심사를 통과했습니다!\n\n"
                    f"{ai_message}\n\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"🏆 최종 점수: {score}점\n"
                    f"⏱ 소요 시간: {session.time_used:.1f}초\n"
                    f"📝 사용 프롬프트: {session.prompt_count}회"
                ),
                level=session.current_level,
                is_game_clear=True,
                score=score,
                prompt_count=session.prompt_count,
                time_used=session.time_used,
            )

    # ── 불합격(fail) 처리 ──
    # 📝 분석 로그: 불합격 응답
    analytics_service.log_chat_interaction(
        session_id=session.session_id,
        level=session.current_level,
        domain=current_config["domain"],
        user_message=message,
        ai_status=status,
        ai_message=ai_message,
        prompt_count=session.prompt_count,
        time_used=session.time_used,
        level_attempt=session.level_attempts[session.current_level],
        missing_criteria=missing_criteria,
        is_level_clear=False,
        is_game_clear=False,
    )

    return ChatResponse(
        status="fail",
        message=ai_message,
        level=session.current_level,
        is_game_clear=False,
        score=None,
        prompt_count=session.prompt_count,
        time_used=session.time_used,
    )


def calculate_score(time_used: float, prompt_count: int) -> int:
    """
    게임 클리어 시 최종 점수를 계산합니다.

    공식: (TIME_LIMIT - time_used) * W_TIME + (P_MAX - prompt_count) * W_PROMPT

    Args:
        time_used: 소요 시간(초)
        prompt_count: 사용한 프롬프트 횟수

    Returns:
        최종 점수 (최소 0점)
    """
    time_score = (TIME_LIMIT - time_used) * W_TIME
    prompt_score = (P_MAX - prompt_count) * W_PROMPT
    total = int(time_score + prompt_score)
    return max(total, 0)  # 음수 방지
