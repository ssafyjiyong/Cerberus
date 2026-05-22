"""
Cerberus: The Dark Auditor - Pydantic 데이터 모델

API 요청/응답에 사용되는 모든 데이터 모델을 정의합니다.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


# ──────────────────────────────────────────────
# 게임 관련 모델
# ──────────────────────────────────────────────

class GameStartResponse(BaseModel):
    """게임 시작 응답 모델"""

    session_id: str = Field(..., description="고유 세션 식별자")
    level: int = Field(..., description="현재 레벨 (1~3)")
    question: str = Field(..., description="심사원의 질문")
    message: str = Field(..., description="안내 메시지")


class ChatRequest(BaseModel):
    """채팅 요청 모델"""

    session_id: str = Field(..., description="세션 식별자")
    message: str = Field(..., min_length=1, description="사용자 답변 메시지")


class ChatResponse(BaseModel):
    """채팅 응답 모델 – AI 심사원의 평가 결과"""

    status: str = Field(..., description="평가 결과 (pass / fail)")
    message: str = Field(..., description="심사원 피드백 메시지")
    level: int = Field(..., description="현재 레벨")
    is_game_clear: bool = Field(default=False, description="게임 클리어 여부")
    score: Optional[int] = Field(default=None, description="최종 점수 (클리어 시)")
    prompt_count: int = Field(..., description="사용한 프롬프트 수")
    time_used: float = Field(..., description="경과 시간(초)")


# ──────────────────────────────────────────────
# 리더보드 관련 모델
# ──────────────────────────────────────────────

class LeaderboardEntry(BaseModel):
    """리더보드 항목 모델"""

    rank: int = Field(..., description="순위")
    name: str = Field(..., description="플레이어 이름")
    score: int = Field(..., description="점수")
    time_used: float = Field(..., description="소요 시간(초)")
    created_at: str = Field(..., description="등록 일시 (ISO 8601)")


class LeaderboardSubmitRequest(BaseModel):
    """리더보드 점수 제출 요청 모델"""

    session_id: str = Field(..., description="세션 식별자")
    name: str = Field(..., min_length=1, max_length=20, description="플레이어 이름")
