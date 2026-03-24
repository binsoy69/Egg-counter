"""Authentication helpers for the FastAPI dashboard."""

from __future__ import annotations

import hashlib
import hmac

from fastapi import HTTPException, Request, status


def hash_password(password: str, salt: str) -> str:
    """Hash a password using the project's scrypt storage format."""
    password_hash = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt.encode("utf-8"),
        n=16384,
        r=8,
        p=1,
    )
    return f"scrypt${salt}${password_hash.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    """Validate a password against a stored scrypt hash."""
    try:
        algorithm, salt, expected_hex = stored_hash.split("$", 2)
    except ValueError:
        return False

    if algorithm != "scrypt" or not salt or not expected_hex:
        return False

    candidate = hash_password(password, salt)
    return hmac.compare_digest(candidate, stored_hash)


def build_session_middleware_config(settings: dict) -> dict:
    """Build SessionMiddleware kwargs from settings."""
    return {
        "secret_key": settings["session_secret"],
        "session_cookie": settings.get(
            "auth_cookie_name", "egg_counter_session"
        ),
        "max_age": int(settings.get("session_max_age", 1209600)),
        "same_site": "lax",
        "https_only": True,
    }


def is_authenticated(request: Request) -> bool:
    """Return whether the request has an authenticated session."""
    return bool(request.session.get("authenticated"))


def require_authenticated_request(request: Request) -> None:
    """Raise 401 when the request is missing an authenticated session."""
    if not is_authenticated(request):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
