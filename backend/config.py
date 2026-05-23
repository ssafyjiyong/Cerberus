"""
Cerberus: The Dark Auditor - 환경 설정 모듈

.env 파일에서 환경 변수를 로드하고 애플리케이션 전역 설정을 관리합니다.
"""

import os
from dotenv import load_dotenv

# 프로젝트 루트의 .env 파일 로드 (backend 상위 디렉토리)
_env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
load_dotenv(dotenv_path=_env_path)

# ──────────────────────────────────────────────
# AWS 설정
# ──────────────────────────────────────────────
AWS_REGION: str = os.getenv("AWS_REGION", "ap-northeast-2")
BEDROCK_MODEL_ID: str = os.getenv(
    "BEDROCK_MODEL_ID", "anthropic.claude-3-haiku-20240307-v1:0"
)
DYNAMODB_TABLE_NAME: str = os.getenv("DYNAMODB_TABLE_NAME", "cerberus-leaderboard")

# ──────────────────────────────────────────────
# 게임 설정
# ──────────────────────────────────────────────
TIME_LIMIT: int = int(os.getenv("TIME_LIMIT", "300"))       # 제한 시간(초)
P_MAX: int = int(os.getenv("P_MAX", "15"))                  # 최대 프롬프트 횟수
W_TIME: int = int(os.getenv("W_TIME", "1"))                 # 시간 가중치
W_PROMPT: int = int(os.getenv("W_PROMPT", "10"))            # 프롬프트 가중치
