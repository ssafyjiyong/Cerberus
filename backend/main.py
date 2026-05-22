"""
Cerberus: The Dark Auditor - FastAPI 메인 애플리케이션

ISMS 인증 심사 시뮬레이션 게임의 백엔드 API 서버입니다.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from routers import game, leaderboard, analytics
from services import dynamo_service, analytics_service

# ──────────────────────────────────────────────
# 로깅 설정
# ──────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(levelname)-7s │ %(name)s │ %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────
# 애플리케이션 라이프사이클
# ──────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 시작/종료 시 실행되는 라이프사이클 핸들러"""
    logger.info("🐕‍🦺 Cerberus: The Dark Auditor 서버를 시작합니다...")

    # AWS 환경에서 DynamoDB 테이블을 확인하고 없으면 생성합니다.
    # 로컬 개발(자격 증명 없음)에서는 실패해도 무시하고 mock 모드로 동작합니다.
    try:
        dynamo_service.ensure_table_exists()
        analytics_service.ensure_log_table_exists()
    except Exception as exc:
        logger.warning(
            "DynamoDB 테이블 초기화를 건너뜁니다 (로컬 개발 모드 추정): %s", exc
        )

    yield
    logger.info("🐕‍🦺 Cerberus: The Dark Auditor 서버를 종료합니다...")


# ──────────────────────────────────────────────
# FastAPI 앱 인스턴스 생성
# ──────────────────────────────────────────────
app = FastAPI(
    title="Cerberus: The Dark Auditor API",
    description=(
        "ISMS 인증 심사 시뮬레이션 게임 API.\n\n"
        "AI 심사원 '케르베로스'와의 ISMS 인증 심사 면접을 시뮬레이션합니다.\n"
        "3단계의 심사 영역을 통과하여 최고 점수를 획득하세요!"
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# ──────────────────────────────────────────────
# CORS 미들웨어 (개발용: 모든 오리진 허용)
# ──────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ──────────────────────────────────────────────
# 라우터 등록
# ──────────────────────────────────────────────
app.include_router(game.router)
app.include_router(leaderboard.router)
app.include_router(analytics.router)


# ──────────────────────────────────────────────
# 헬스 체크 엔드포인트
# ──────────────────────────────────────────────
@app.get(
    "/api/health",
    tags=["시스템"],
    summary="서버 상태 확인",
    description="서버의 정상 동작 여부를 확인합니다.",
)
async def health_check() -> dict:
    """서버 상태를 반환합니다."""
    return {
        "status": "healthy",
        "service": "Cerberus: The Dark Auditor",
        "version": "1.0.0",
    }


# ──────────────────────────────────────────────
# 전역 예외 핸들러
# ──────────────────────────────────────────────
@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
    """ValueError를 400 Bad Request로 변환합니다."""
    logger.warning("ValueError 발생 [%s]: %s", request.url, exc)
    return JSONResponse(
        status_code=400,
        content={"detail": str(exc)},
    )


@app.exception_handler(RuntimeError)
async def runtime_error_handler(request: Request, exc: RuntimeError) -> JSONResponse:
    """RuntimeError를 503 Service Unavailable로 변환합니다."""
    logger.error("RuntimeError 발생 [%s]: %s", request.url, exc)
    return JSONResponse(
        status_code=503,
        content={"detail": "서비스를 일시적으로 사용할 수 없습니다. 잠시 후 다시 시도해 주세요."},
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """처리되지 않은 예외를 500 Internal Server Error로 변환합니다."""
    logger.error("예상치 못한 오류 [%s]: %s", request.url, exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "서버 내부 오류가 발생했습니다."},
    )


# ──────────────────────────────────────────────
# 직접 실행 시 uvicorn 서버 가동
# ──────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
