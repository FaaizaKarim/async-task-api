"""Authentication: PBKDF2 password hashing + JWT bearer tokens.

Secure-coding practices applied here:
  * passwords hashed with PBKDF2-HMAC-SHA256, per-user random salt,
    600k iterations (OWASP recommendation) — never stored in plaintext;
  * constant-time comparison (hmac.compare_digest) to prevent timing attacks;
  * JWTs are short-lived and signed with a server-side secret;
  * token subject is looked up on every request — deleted users lose access.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import hmac
import secrets

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .config import settings
from .database import get_session
from .models import User

_PBKDF2_ITERATIONS = 600_000
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


# --- password hashing (stdlib only: hashlib + hmac) ---

def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), salt.encode(), _PBKDF2_ITERATIONS
    ).hex()
    return f"pbkdf2_sha256${_PBKDF2_ITERATIONS}${salt}${digest}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _algo, iterations, salt, digest = stored.split("$")
        candidate = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), salt.encode(), int(iterations)
        ).hex()
        return hmac.compare_digest(candidate, digest)
    except (ValueError, TypeError):
        return False


# --- JWT ---

def create_access_token(user_id: int) -> str:
    now = dt.datetime.now(dt.timezone.utc)
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + dt.timedelta(minutes=settings.access_token_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_session),
) -> User:
    """Dependency: resolve the bearer token to a live User row."""
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
        user_id = int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise credentials_error

    user = await session.scalar(select(User).where(User.id == user_id))
    if user is None:
        raise credentials_error
    return user
