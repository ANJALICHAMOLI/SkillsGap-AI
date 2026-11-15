"""Password and token helpers for the API authentication endpoints."""

from __future__ import annotations

import hashlib
import os
import secrets
import warnings
from datetime import datetime, timedelta, timezone
from pathlib import Path

import jwt
from dotenv import load_dotenv
from pwdlib import PasswordHash

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_MINUTES = 15
REFRESH_TOKEN_DAYS = 30
password_hash = PasswordHash.recommended()

APP_ENV = os.getenv("APP_ENV", "development").strip().lower()
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "").strip()
PLACEHOLDER_SECRETS = {
    "replace-with-a-long-random-secret",
    "change-me",
    "your-secret-key",
}

if JWT_SECRET_KEY and (
    len(JWT_SECRET_KEY) < 32
    or JWT_SECRET_KEY.lower() in PLACEHOLDER_SECRETS
    or JWT_SECRET_KEY.lower().startswith("replace-with-")
):
    raise RuntimeError("JWT_SECRET_KEY must be a non-placeholder value of at least 32 characters.")

if not JWT_SECRET_KEY:
    if APP_ENV == "production":
        raise RuntimeError("JWT_SECRET_KEY must be set when APP_ENV=production.")
    JWT_SECRET_KEY = secrets.token_urlsafe(48)
    warnings.warn(
        "JWT_SECRET_KEY is unset; authentication tokens will become invalid when the server restarts. "
        "Set JWT_SECRET_KEY in the backend environment for persistent sessions.",
        RuntimeWarning,
        stacklevel=2,
    )


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, stored_hash: str) -> bool:
    return password_hash.verify(password, stored_hash)


def create_access_token(user_id: int) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(minutes=ACCESS_TOKEN_MINUTES),
        "type": "access",
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> int:
    payload = jwt.decode(
        token,
        JWT_SECRET_KEY,
        algorithms=[JWT_ALGORITHM],
        options={"require": ["sub", "exp", "iat", "type"]},
    )
    if payload.get("type") != "access":
        raise jwt.InvalidTokenError("Wrong token type")
    try:
        return int(payload["sub"])
    except (TypeError, ValueError) as exc:
        raise jwt.InvalidTokenError("Invalid subject") from exc


def create_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def refresh_token_expiry() -> datetime:
    return datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_DAYS)
