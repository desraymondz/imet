from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt
from starlette.responses import Response

from backend.config import settings

# Cookie the browser stores and sends on later requests. HttpOnly so JS cannot read it.
ACCESS_COOKIE_NAME = "access_token"


def hash_password(plain: str) -> str:
    """Hash a plain text password."""
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plain text password against a hashed password."""
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def create_access_token(data: dict) -> str:
    """Create a JWT access token with payload data."""
    payload = data.copy()
    # Set the expiry time of the token
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    payload["exp"] = expire

    # Encode the payload into a JWT token
    token = jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)
    return token


def decode_access_token(token: str) -> dict | None:
    """Verifies the signature and expiry of a JWT access token and return the payload if valid, otherwise return None"""
    try:
        # Decode the JWT token and return the payload
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        return payload
    except JWTError:
        # If the token is invalid, return None
        return None


def set_auth_cookie(response: Response, token: str) -> None:
    """Store the JWT in an HTTP-only cookie."""
    response.set_cookie(
        key=ACCESS_COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        path="/",
        max_age=settings.access_token_expire_minutes * 60,
        secure=settings.cookie_secure,
    )


def clear_auth_cookie(response: Response) -> None:
    """Clear the auth cookie on logout."""
    response.delete_cookie(
        key=ACCESS_COOKIE_NAME,
        path="/",
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
    )
