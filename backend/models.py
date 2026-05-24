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

class GameStartRequest(BaseModel):
    """게임 시작 요청 모델 — 각 단계가 독립 세션이므로 어느 단계를 시작할지 지정."""

    level: int = Field(default=1, ge=1, le=3, description="시작할 레벨 (1~3)")


class GameStartResponse(BaseModel):
    """게임 시작 응답 모델 — 한 단계용 세션 정보."""

    session_id: str = Field(..., description="고유 세션 식별자 (단계별)")
    level: int = Field(..., description="이 세션이 다루는 레벨 (1~3)")
    domain: str = Field(..., description="이 단계의 심사 영역")
    question: str = Field(..., description="심사원의 질문")
    message: str = Field(..., description="안내 메시지")
    time_limit: int = Field(..., description="이 단계의 제한 시간(초)")
    p_max: int = Field(..., description="이 단계의 최대 답변 횟수")
    pass_logic: str = Field(default="AND", description="이 단계의 통과 판정 방식 (AND/OR)")


class ChatRequest(BaseModel):
    """채팅 요청 모델"""

    session_id: str = Field(..., description="세션 식별자")
    message: str = Field(..., min_length=1, description="사용자 답변 메시지")


class ChatResponse(BaseModel):
    """채팅 응답 모델 – AI 심사원의 평가 결과 (단계 단위)."""

    status: str = Field(..., description="평가 결과 (pass / fail)")
    message: str = Field(..., description="심사원 피드백 메시지")
    level: int = Field(..., description="이 세션이 다루는 레벨")
    is_stage_clear: bool = Field(
        default=False, description="이 단계를 통과했는지 여부 (pass 와 동의)"
    )
    score: Optional[int] = Field(default=None, description="이 단계의 점수 (통과 시)")
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
    """
    리더보드 점수 제출 요청 모델.

    각 단계가 독립 세션이므로, 클리어한 모든 단계의 session_id 를 함께 넘깁니다.
    백엔드는 세션이 모두 통과되었는지 검증한 뒤 점수와 시간을 합산하여 등록합니다.
    """

    session_ids: list[str] = Field(
        ..., min_length=1, description="클리어한 모든 단계의 세션 ID 목록"
    )
    name: str = Field(..., min_length=1, max_length=20, description="플레이어 이름")
