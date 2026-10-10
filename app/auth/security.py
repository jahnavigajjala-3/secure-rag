import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import jwt

from app.config import settings

JWT_SECRET_KEY = settings.JWT_SECRET_KEY
JWT_ALGORITHM = settings.JWT_ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES


def ensure_secret_config() -> str:
    if not JWT_SECRET_KEY:
        raise RuntimeError("JWT_SECRET_KEY is required. Set it in your environment before starting SecureRAG.")
    if settings.is_production() and (len(JWT_SECRET_KEY) < 32 or JWT_SECRET_KEY in {"", "changeme", "secure_rag_dev_jwt_secret_key_change_in_production"}):
        raise RuntimeError("JWT_SECRET_KEY must be set to a strong secret in production.")
    return JWT_SECRET_KEY


def hash_password(password: str) -> str:
    import bcrypt

    if not password:
        raise ValueError("Password must not be empty.")
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    if not plain_password or not hashed_password:
        return False
    try:
        import bcrypt
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire, "iat": now})
    return jwt.encode(to_encode, ensure_secret_config(), algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> Dict[str, Any]:
    return jwt.decode(token, ensure_secret_config(), algorithms=[JWT_ALGORITHM])
