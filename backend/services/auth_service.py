"""
Cerberus: The Dark Auditor - 관리자 인증 서비스

bcrypt 기반 비밀번호 해싱 + 인메모리 베어러 토큰 발급/검증.
토큰은 8시간 후 자동 만료되며, 서버 재시작 시 모두 무효화됩니다.
"""

from __future__ import annotations

import logging
import secrets
import time
from threading import Lock

import bcrypt

logger = logging.getLogger(__name__)

TOKEN_TTL_SECONDS = 8 * 60 * 60  # 8시간

_tokens: dict[str, float] = {}  # token → expires_at(timestamp)
_lock = Lock()


def hash_password(plaintext: str) -> str:
    """평문 비밀번호를 bcrypt 해시로 변환."""
    return bcrypt.hashpw(plaintext.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plaintext: str, stored_hash: str) -> bool:
    """평문이 저장된 해시와 일치하는지 확인."""
    if not plaintext or not stored_hash:
        return False
    try:
        return bcrypt.checkpw(
            plaintext.encode("utf-8"), stored_hash.encode("utf-8")
        )
    except (ValueError, TypeError) as exc:
        logger.warning("비밀번호 검증 실패: %s", exc)
        return False


def issue_token() -> str:
    """새 베어러 토큰을 발급."""
    token = secrets.token_urlsafe(32)
    with _lock:
        _tokens[token] = time.time() + TOKEN_TTL_SECONDS
        _cleanup_expired_locked()
    return token


def verify_token(token: str) -> bool:
    """토큰이 유효(미만료)한지 확인."""
    if not token:
        return False
    with _lock:
        expires_at = _tokens.get(token)
        if expires_at is None:
            return False
        if expires_at < time.time():
            _tokens.pop(token, None)
            return False
        return True


def revoke_token(token: str) -> None:
    """토큰을 무효화 (로그아웃)."""
    with _lock:
        _tokens.pop(token, None)


def _cleanup_expired_locked() -> None:
    """만료된 토큰 일괄 정리 (락이 잡힌 상태에서 호출)."""
    now = time.time()
    expired = [t for t, exp in _tokens.items() if exp < now]
    for t in expired:
        _tokens.pop(t, None)
