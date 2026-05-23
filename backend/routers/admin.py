"""
Cerberus: The Dark Auditor - 관리자 라우터

게임 설정·문제·리더보드를 런타임에 관리하는 비공개 API.
모든 엔드포인트는 `/api/admin/auth/login` 으로 발급받은 베어러 토큰이 필요합니다.
"""

from __future__ import annotations

import logging
from typing import Optional

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


class LevelConfigUpdate(BaseModel):
    domain: Optional[str] = None
    question: Optional[str] = None
    pass_criteria: Optional[list[str]] = None


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


class GenerateQuestionRequest(BaseModel):
    level: int = Field(..., ge=1, le=3)
    hint: str = ""


class GenerateCriteriaRequest(BaseModel):
    question: str = Field(..., min_length=1)
    domain: str = ""


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
    auth_service.revoke_token(token)  # 보안: 변경 후 기존 토큰 무효화
    return {"success": True, "message": "비밀번호가 변경되었습니다. 다시 로그인하세요."}


# ──────────────────────────────────────────────
# 설정 조회/변경
# ──────────────────────────────────────────────
@router.get("/config", summary="전체 설정 조회")
async def get_full_config(token: str = Depends(require_admin)) -> dict:
    cfg = config_service.get_config()
    cfg.pop("admin_password_hash", None)  # 클라이언트에 해시 노출 금지
    return cfg


@router.put("/config/levels/{level}", summary="레벨 문제 수정")
async def update_level(
    level: int, req: LevelConfigUpdate, token: str = Depends(require_admin)
) -> dict:
    if level not in (1, 2, 3):
        raise HTTPException(status_code=400, detail="유효한 레벨이 아닙니다 (1~3).")
    updates = req.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="수정할 항목이 없습니다.")
    if "pass_criteria" in updates and not updates["pass_criteria"]:
        raise HTTPException(status_code=400, detail="pass_criteria 는 비어있을 수 없습니다.")
    config_service.update_level_config(level, updates)
    return {"success": True, "level": level, "updated": list(updates.keys())}


@router.post("/config/levels/import", summary="레벨 문제 전체 일괄 교체 (JSON import)")
async def import_levels(
    req: LevelConfigsImport, token: str = Depends(require_admin)
) -> dict:
    parsed: dict[int, dict] = {}
    for k, v in req.level_configs.items():
        try:
            level_int = int(k)
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail=f"레벨 키 '{k}' 가 정수가 아닙니다.")
        if level_int not in (1, 2, 3):
            raise HTTPException(status_code=400, detail=f"레벨 키 '{k}' 가 유효하지 않습니다 (1~3).")
        if not isinstance(v, dict):
            raise HTTPException(status_code=400, detail=f"레벨 {k} 값이 객체가 아닙니다.")
        if not v.get("question") or not v.get("domain"):
            raise HTTPException(status_code=400, detail=f"레벨 {k}: domain·question 은 필수입니다.")
        if not isinstance(v.get("pass_criteria"), list) or not v["pass_criteria"]:
            raise HTTPException(
                status_code=400,
                detail=f"레벨 {k}: pass_criteria 는 비어있지 않은 리스트여야 합니다.",
            )
        parsed[level_int] = v
    if set(parsed.keys()) != {1, 2, 3}:
        raise HTTPException(status_code=400, detail="레벨 1·2·3 모두 포함되어야 합니다.")
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
# AI 어시스트
# ──────────────────────────────────────────────
@router.post("/ai/generate-question", summary="AI 로 새 심사 질문 생성")
async def ai_generate_question(
    req: GenerateQuestionRequest, token: str = Depends(require_admin)
) -> dict:
    try:
        q = bedrock_service.generate_question(req.level, req.hint)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=f"AI 서비스 오류: {exc}") from exc
    if not q:
        raise HTTPException(status_code=502, detail="AI가 질문을 생성하지 못했습니다.")
    return {"question": q}


@router.post("/ai/generate-criteria", summary="AI 로 통과 기준 3가지 생성")
async def ai_generate_criteria(
    req: GenerateCriteriaRequest, token: str = Depends(require_admin)
) -> dict:
    try:
        criteria = bedrock_service.generate_pass_criteria(req.question, req.domain)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=f"AI 서비스 오류: {exc}") from exc
    if not criteria:
        raise HTTPException(status_code=502, detail="AI가 통과 기준을 생성하지 못했습니다.")
    return {"criteria": criteria}


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
