from __future__ import annotations
from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from fastapi import Cookie, HTTPException, status
from src.config import settings

_SECRET = settings.admin_secret_key
_ALGORITHM = "HS256"
_EXPIRE_HOURS = 24
_COOKIE_NAME = "admin_token"


def create_token() -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=_EXPIRE_HOURS)
    return jwt.encode({"sub": "admin", "exp": expire}, _SECRET, algorithm=_ALGORITHM)


def verify_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, _SECRET, algorithms=[_ALGORITHM])
    except JWTError:
        return None


def require_admin(admin_token: Optional[str] = Cookie(default=None)):
    if not admin_token or not verify_token(admin_token):
        raise HTTPException(
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
            headers={"Location": "/admin/login"},
        )
    return True
