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
    exclude_question_ids: Optional[list[str]] = Field(
        default=None,
        description=(
            "같은 게임 안에서 이미 출제된 질문 ID 목록. "
            "전체 풀 랜덤 출제 시 중복 방지를 위해 클라이언트가 누적해서 전달합니다."
        ),
    )


class GameStartResponse(BaseModel):
    """게임 시작 응답 모델 — 한 단계용 세션 정보 + 출제된 질문."""

    session_id: str = Field(..., description="고유 세션 식별자 (단계별)")
    level: int = Field(..., description="이 세션이 다루는 레벨 (1~3)")
    title: str = Field(..., description="이 단계의 표시 제목")
    subtitle: str = Field(default="", description="이 단계의 부제(영역 설명)")

    # 출제된 ISMS-P 시나리오 질문
    question_id: str = Field(default="", description="출제된 질문의 고유 ID (중복 방지용)")
    isms_control_id: str = Field(default="", description="근거 ISMS-P 항목 ID (예: 2.6.2)")
    isms_control_title: str = Field(default="", description="ISMS-P 항목 이름")
    scenario_context: str = Field(default="", description="시나리오 컨텍스트 (왜 지적되었는지)")
    question: str = Field(..., description="심사원이 던지는 질문")

    message: str = Field(..., description="안내 메시지")
    time_limit: int = Field(..., description="이 단계의 제한 시간(초)")
    p_max: int = Field(..., description="이 단계의 최대 답변 횟수")

    # 하위 호환을 위해 유지 (구 프론트엔드에서 domain 사용)
    domain: str = Field(default="", description="(legacy) 심사 영역명. subtitle 와 동일하게 채움.")


class ChatRequest(BaseModel):
    """채팅 요청 모델"""

    session_id: str = Field(..., description="세션 식별자")
    message: str = Field(..., min_length=1, description="사용자 답변 메시지")


class ChatResponse(BaseModel):
    """채팅 응답 모델 – AI 심사원의 평가 결과 (단계 단위)."""

    status: str = Field(..., description="(legacy) 평가 결과 — fail 또는 pass(=full/half)")
    tier: str = Field(default="fail", description="full | half | fail")
    matched_path_id: str = Field(default="", description="full/half 시 매칭된 answer_path id")
    message: str = Field(..., description="심사원 피드백 메시지")
    level: int = Field(..., description="이 세션이 다루는 레벨")
    is_stage_clear: bool = Field(
        default=False, description="이 단계를 통과했는지 여부 (full 또는 half)"
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

    클리어한 단계(full 또는 half)의 session_id 를 모두 보냅니다. 모든 단계를 다
    클리어하지 못해도, **1점 이상 누적**이면 등록 가능합니다.
    """

    session_ids: list[str] = Field(
        ..., min_length=1, description="클리어한 단계들의 세션 ID 목록"
    )
    name: str = Field(..., min_length=1, max_length=20, description="플레이어 이름")
