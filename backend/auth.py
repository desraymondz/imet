from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt

from backend.config import settings


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
