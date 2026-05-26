"""
Cerberus: The Dark Auditor - 관리자 라우터

게임 설정·문제·리더보드를 런타임에 관리하는 비공개 API.
모든 엔드포인트는 `/api/admin/auth/login` 으로 발급받은 베어러 토큰이 필요합니다.

v2 — 질문 풀 기반:
  - 스테이지 = 3개 고정 (1·2·3)
  - 각 스테이지는 메타(title/p_max/time_limit/base_score) + 질문 풀(N개)
  - 질문 단위 CRUD: GET/POST/PUT/DELETE /config/stages/{stage}/questions
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field

from services import (
    analytics_service,
    auth_service,
    bedrock_service,
    config_service,
    dynamo_service,
    game_service,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin", tags=["관리자"])


# ──────────────────────────────────────────────
# 인증 의존성
# ──────────────────────────────────────────────
def require_admin(authorization: Optional[str] = Header(None)) -> str:
    """Bearer 토큰 검증 의존성."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="관리자 인증이 필요합니다.")
    token = authorization[len("Bearer "):].strip()
    if not auth_service.verify_token(token):
        raise HTTPException(status_code=401, detail="유효하지 않거나 만료된 토큰입니다.")
    return token


# ──────────────────────────────────────────────
# 요청 모델
# ──────────────────────────────────────────────
class LoginRequest(BaseModel):
    password: str = Field(..., min_length=1)


class PasswordChangeRequest(BaseModel):
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=4, max_length=128)


class StageMetaUpdate(BaseModel):
    title: Optional[str] = None
    subtitle: Optional[str] = None
    time_limit: Optional[int] = Field(default=None, ge=0, le=3600)
    p_max: Optional[int] = Field(default=None, ge=0, le=100)
    base_score: Optional[int] = Field(default=None, ge=0, le=1_000_000)


class AnswerPathPayload(BaseModel):
    """answer_path 1건의 페이로드. 어떤 필드가 의미를 가질지는 tier 에 따라 다름."""

    id: Optional[str] = None
    tier: str = Field(..., description="full | half | fail")
    description: Optional[str] = ""
    trigger_keywords: Optional[list[str]] = Field(default_factory=list)
    required_keyword_min: Optional[int] = Field(
        default=0, ge=0, le=20,
        description="trigger_keywords 중 최소 매칭 개수 (0=1개 이상이면 통과).",
    )
    rebuttal: Optional[str] = ""
    acknowledgment_keywords: Optional[list[str]] = Field(default_factory=list)
    acknowledgment_min: Optional[int] = Field(
        default=0, ge=0, le=20,
        description="half 경로의 acknowledgment 최소 매칭 개수 (0=1).",
    )
    follow_up: Optional[str] = ""
    compensating_keywords: Optional[list[str]] = Field(default_factory=list)
    compensating_min: Optional[int] = Field(
        default=0, ge=0, le=20,
        description="full 경로의 compensating 최소 매칭 개수 (0=전체 충족 필요).",
    )
    exemplar_answer: Optional[str] = ""


class QuestionPayload(BaseModel):
    id: Optional[str] = None
    isms_control_id: str = ""
    isms_control_title: str = ""
    scenario_context: str = ""
    auditor_question: str = Field(..., min_length=1)
    default_rebuttal: Optional[str] = ""
    answer_paths: list[AnswerPathPayload] = Field(..., min_length=1)


class LevelConfigsImport(BaseModel):
    level_configs: dict[str, dict]


class GameParamsUpdate(BaseModel):
    TIME_LIMIT: Optional[int] = Field(default=None, ge=30, le=3600)
    P_MAX: Optional[int] = Field(default=None, ge=1, le=100)
    W_TIME: Optional[int] = Field(default=None, ge=0, le=100)
    W_PROMPT: Optional[int] = Field(default=None, ge=0, le=1000)
    BEDROCK_MODEL_ID: Optional[str] = Field(default=None, min_length=1, max_length=256)


class MaintenanceRequest(BaseModel):
    enabled: bool


class ResetRequest(BaseModel):
    reset_password: bool = False


class GenerateScenarioRequest(BaseModel):
    isms_control_id: str = ""
    isms_control_title: str = ""
    hint: str = ""


class GenerateAuditorQuestionRequest(BaseModel):
    scenario: str = Field(..., min_length=1)
    isms_control_title: str = ""


class GenerateAnswerPathsRequest(BaseModel):
    scenario: str = Field(..., min_length=1)
    auditor_question: str = Field(..., min_length=1)
    isms_control_title: str = ""


class PolishRequest(BaseModel):
    text: str = Field(..., min_length=1)
    kind: str = Field(default="question")


# ──────────────────────────────────────────────
# 인증
# ──────────────────────────────────────────────
@router.post("/auth/login", summary="관리자 로그인 → 토큰 발급")
async def login(req: LoginRequest) -> dict:
    stored_hash = config_service.get_admin_password_hash()
    if not auth_service.verify_password(req.password, stored_hash):
        raise HTTPException(status_code=401, detail="비밀번호가 올바르지 않습니다.")
    token = auth_service.issue_token()
    return {
        "token": token,
        "expires_in_seconds": auth_service.TOKEN_TTL_SECONDS,
    }


@router.post("/auth/logout", summary="관리자 로그아웃")
async def logout(token: str = Depends(require_admin)) -> dict:
    auth_service.revoke_token(token)
    return {"success": True}


@router.post("/auth/password", summary="관리자 비밀번호 변경")
async def change_password(
    req: PasswordChangeRequest, token: str = Depends(require_admin)
) -> dict:
    current_hash = config_service.get_admin_password_hash()
    if not auth_service.verify_password(req.current_password, current_hash):
        raise HTTPException(status_code=400, detail="현재 비밀번호가 일치하지 않습니다.")
    if req.new_password == req.current_password:
        raise HTTPException(status_code=400, detail="새 비밀번호는 기존과 달라야 합니다.")
    config_service.set_admin_password_hash(auth_service.hash_password(req.new_password))
    auth_service.revoke_token(token)
    return {"success": True, "message": "비밀번호가 변경되었습니다. 다시 로그인하세요."}


# ──────────────────────────────────────────────
# 설정 조회/변경
# ──────────────────────────────────────────────
@router.get("/config", summary="전체 설정 조회")
async def get_full_config(token: str = Depends(require_admin)) -> dict:
    cfg = config_service.get_config()
    cfg.pop("admin_password_hash", None)
    # level_configs 를 정규화된 형태로 반환 (구버전 데이터도 v2 형식으로 변환되어 나옴)
    cfg["level_configs"] = {
        str(stage): config_service.get_stage_config(stage)
        for stage in config_service.ALLOWED_STAGES
    }
    return cfg


# ──────────────────────────────────────────────
# 스테이지 메타 수정
# ──────────────────────────────────────────────
@router.put("/config/stages/{stage}/meta", summary="스테이지 메타 수정")
async def update_stage_meta(
    stage: int, req: StageMetaUpdate, token: str = Depends(require_admin)
) -> dict:
    if stage not in config_service.ALLOWED_STAGES:
        raise HTTPException(status_code=400, detail="유효한 스테이지가 아닙니다 (1~3).")
    updates = req.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="수정할 항목이 없습니다.")
    try:
        config_service.update_stage_meta(stage, updates)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"success": True, "stage": stage, "updated": list(updates.keys())}


# ──────────────────────────────────────────────
# 질문 풀 CRUD
# ──────────────────────────────────────────────
@router.get("/config/stages/{stage}/questions", summary="스테이지 질문 풀 조회")
async def list_questions(
    stage: int, token: str = Depends(require_admin)
) -> dict:
    if stage not in config_service.ALLOWED_STAGES:
        raise HTTPException(status_code=400, detail="유효한 스테이지가 아닙니다 (1~3).")
    return {"stage": stage, "questions": config_service.list_questions(stage)}


@router.post("/config/stages/{stage}/questions", summary="질문 추가")
async def add_question(
    stage: int, req: QuestionPayload, token: str = Depends(require_admin)
) -> dict:
    if stage not in config_service.ALLOWED_STAGES:
        raise HTTPException(status_code=400, detail="유효한 스테이지가 아닙니다 (1~3).")
    try:
        created = config_service.add_question(stage, req.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"success": True, "stage": stage, "question": created}


@router.put(
    "/config/stages/{stage}/questions/{question_id}",
    summary="질문 수정 (전체 교체)",
)
async def update_question(
    stage: int, question_id: str, req: QuestionPayload,
    token: str = Depends(require_admin),
) -> dict:
    if stage not in config_service.ALLOWED_STAGES:
        raise HTTPException(status_code=400, detail="유효한 스테이지가 아닙니다 (1~3).")
    try:
        updated = config_service.update_question(stage, question_id, req.model_dump())
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"success": True, "stage": stage, "question": updated}


@router.delete(
    "/config/stages/{stage}/questions/{question_id}",
    summary="질문 삭제",
)
async def delete_question(
    stage: int, question_id: str, token: str = Depends(require_admin)
) -> dict:
    if stage not in config_service.ALLOWED_STAGES:
        raise HTTPException(status_code=400, detail="유효한 스테이지가 아닙니다 (1~3).")
    try:
        config_service.delete_question(stage, question_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"success": True, "stage": stage, "deleted_id": question_id}


class ReseedRequest(BaseModel):
    mode: str = Field(default="replace", description='"replace" 또는 "merge"')


@router.post(
    "/config/stages/{stage}/reseed",
    summary="스테이지 풀을 기본 시드로 재적용",
    description=(
        "mode=replace(기본): 기존 풀을 시드로 완전히 교체. "
        "mode=merge: 시드 중 ID가 중복되지 않은 항목만 추가(사용자 커스텀 보존)."
    ),
)
async def reseed_stage(
    stage: int, req: ReseedRequest, token: str = Depends(require_admin)
) -> dict:
    if stage not in config_service.ALLOWED_STAGES:
        raise HTTPException(status_code=400, detail="유효한 스테이지가 아닙니다 (1~3).")
    if req.mode not in ("replace", "merge"):
        raise HTTPException(status_code=400, detail='mode 는 "replace" 또는 "merge" 여야 합니다.')
    try:
        stage_cfg = config_service.reseed_stage(stage, mode=req.mode)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "success": True,
        "stage": stage,
        "mode": req.mode,
        "question_count": len(stage_cfg.get("questions", [])),
    }


@router.post(
    "/config/reseed-all",
    summary="모든 스테이지 풀을 기본 시드로 재적용",
)
async def reseed_all(
    req: ReseedRequest, token: str = Depends(require_admin)
) -> dict:
    if req.mode not in ("replace", "merge"):
        raise HTTPException(status_code=400, detail='mode 는 "replace" 또는 "merge" 여야 합니다.')
    out = config_service.reseed_all_stages(mode=req.mode)
    counts = {stage: len(cfg.get("questions", [])) for stage, cfg in out.items()}
    total = sum(counts.values())
    return {
        "success": True,
        "mode": req.mode,
        "per_stage_count": counts,
        "total_count": total,
        "message": f"전체 {total}개의 기본 시드 질문이 적용되었습니다.",
    }


@router.post("/config/levels/import", summary="레벨 설정 전체 일괄 교체 (JSON import)")
async def import_levels(
    req: LevelConfigsImport, token: str = Depends(require_admin)
) -> dict:
    parsed: dict[int, dict] = {}
    for k, v in req.level_configs.items():
        try:
            stage_int = int(k)
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail=f"스테이지 키 '{k}' 가 정수가 아닙니다.")
        if stage_int not in config_service.ALLOWED_STAGES:
            raise HTTPException(
                status_code=400, detail=f"스테이지 키 '{k}' 가 유효하지 않습니다 (1~3)."
            )
        if not isinstance(v, dict):
            raise HTTPException(status_code=400, detail=f"스테이지 {k} 값이 객체가 아닙니다.")
        parsed[stage_int] = v
    if set(parsed.keys()) != set(config_service.ALLOWED_STAGES):
        raise HTTPException(status_code=400, detail="스테이지 1·2·3 모두 포함되어야 합니다.")
    config_service.replace_all_level_configs(parsed)
    return {"success": True, "imported_levels": sorted(parsed.keys())}


@router.put("/config/game-params", summary="게임 파라미터 수정")
async def update_game_params_endpoint(
    req: GameParamsUpdate, token: str = Depends(require_admin)
) -> dict:
    updates = req.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="수정할 항목이 없습니다.")
    config_service.update_game_params(updates)
    return {"success": True, "updated": list(updates.keys())}


@router.put("/config/maintenance", summary="유지보수 모드 on/off")
async def set_maintenance(
    req: MaintenanceRequest, token: str = Depends(require_admin)
) -> dict:
    config_service.set_maintenance_mode(req.enabled)
    return {"success": True, "maintenance_mode": req.enabled}


@router.post("/config/reset", summary="모든 설정을 코드 기본값으로 복원")
async def reset_defaults(
    req: ResetRequest, token: str = Depends(require_admin)
) -> dict:
    config_service.reset_to_defaults(reset_password=req.reset_password)
    if req.reset_password:
        auth_service.revoke_token(token)
    return {
        "success": True,
        "reset_password": req.reset_password,
        "message": (
            "기본값으로 복원되었습니다. 비밀번호가 초기화되어 다시 로그인이 필요합니다."
            if req.reset_password
            else "기본값으로 복원되었습니다."
        ),
    }


# ──────────────────────────────────────────────
# AI 어시스트 (시나리오 기반)
# ──────────────────────────────────────────────
@router.post("/ai/generate-scenario", summary="AI 로 ISMS-P 시나리오 1문단 생성")
async def ai_generate_scenario(
    req: GenerateScenarioRequest, token: str = Depends(require_admin)
) -> dict:
    if not req.isms_control_id and not req.isms_control_title:
        raise HTTPException(status_code=400, detail="ISMS-P 항목 ID 또는 이름이 필요합니다.")
    try:
        s = bedrock_service.generate_scenario(
            req.isms_control_id, req.isms_control_title, req.hint
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=f"AI 서비스 오류: {exc}") from exc
    if not s:
        raise HTTPException(status_code=502, detail="AI가 시나리오를 생성하지 못했습니다.")
    return {"scenario": s}


@router.post("/ai/generate-question", summary="AI 로 심사원 질문 생성")
async def ai_generate_question(
    req: GenerateAuditorQuestionRequest, token: str = Depends(require_admin)
) -> dict:
    try:
        q = bedrock_service.generate_auditor_question(req.scenario, req.isms_control_title)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=f"AI 서비스 오류: {exc}") from exc
    if not q:
        raise HTTPException(status_code=502, detail="AI가 질문을 생성하지 못했습니다.")
    return {"question": q}


@router.post("/ai/generate-answer-paths", summary="AI 로 answer_paths 자동 생성")
async def ai_generate_answer_paths(
    req: GenerateAnswerPathsRequest, token: str = Depends(require_admin)
) -> dict:
    try:
        paths = bedrock_service.generate_answer_paths(
            req.scenario, req.auditor_question, req.isms_control_title
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=f"AI 서비스 오류: {exc}") from exc
    if not paths:
        raise HTTPException(status_code=502, detail="AI가 answer_paths 를 생성하지 못했습니다.")
    return {"answer_paths": paths}


@router.post("/ai/polish", summary="AI 로 문장 다듬기")
async def ai_polish(
    req: PolishRequest, token: str = Depends(require_admin)
) -> dict:
    try:
        polished = bedrock_service.polish_text(req.text, req.kind)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=f"AI 서비스 오류: {exc}") from exc
    if not polished:
        raise HTTPException(status_code=502, detail="AI가 다듬기 결과를 생성하지 못했습니다.")
    return {"text": polished}


# ──────────────────────────────────────────────
# 분석 / 모니터링
# ──────────────────────────────────────────────
@router.get("/analytics/summary", summary="분석 요약 (관리자용)")
async def admin_analytics_summary(token: str = Depends(require_admin)) -> dict:
    return analytics_service.get_analytics_summary()


@router.get("/analytics/logs", summary="최근 게임 로그 조회")
async def admin_logs(
    limit: int = 100, token: str = Depends(require_admin)
) -> dict:
    logs = analytics_service.list_all_logs()
    logs.sort(key=lambda l: str(l.get("created_at", "")), reverse=True)
    if limit < 1:
        limit = 100
    return {"total": len(logs), "logs": logs[:limit]}


@router.get("/sessions/active", summary="현재 활성 세션 목록 (라이브 모니터링)")
async def admin_active_sessions(token: str = Depends(require_admin)) -> dict:
    sessions = game_service.get_active_sessions()
    by_level = {1: 0, 2: 0, 3: 0}
    for s in sessions:
        lv = s.get("current_level", 0)
        by_level[lv] = by_level.get(lv, 0) + 1
    return {"count": len(sessions), "by_level": by_level, "sessions": sessions}


# ──────────────────────────────────────────────
# 리더보드 관리
# ──────────────────────────────────────────────
@router.get("/leaderboard", summary="리더보드 전체 조회 (id 포함)")
async def admin_leaderboard(token: str = Depends(require_admin)) -> dict:
    entries = dynamo_service.list_all_entries()
    return {"total": len(entries), "entries": entries}


@router.delete("/leaderboard/{entry_id}", summary="리더보드 항목 개별 삭제")
async def admin_delete_entry(
    entry_id: str, token: str = Depends(require_admin)
) -> dict:
    if not dynamo_service.delete_leaderboard_entry(entry_id):
        raise HTTPException(status_code=500, detail="삭제 실패")
    return {"success": True, "deleted": entry_id}


@router.post("/leaderboard/clear", summary="리더보드 전체 초기화")
async def admin_clear_leaderboard(token: str = Depends(require_admin)) -> dict:
    return {"success": True, "deleted_count": dynamo_service.clear_leaderboard()}
