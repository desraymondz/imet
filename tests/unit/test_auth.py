# Unit tests for auth: 
# - JWT handling (backend/auth.py)
# - Register validation (backend/schemas.py)

from datetime import datetime, timedelta, timezone

import pytest
from jose import jwt
from pydantic import ValidationError

from backend.auth import create_access_token, decode_access_token
from backend.config import settings
from backend.schemas import PASSWORD_MAX_LENGTH, PASSWORD_MIN_LENGTH, RegisterRequest


# JWT access tokens

def test_expired_token_is_rejected():
    """Ensure an expired token is rejected."""
    expired = datetime.now(timezone.utc) - timedelta(minutes=1)
    token = jwt.encode(
        {"sub": "alice@test.com", "exp": expired},
        settings.secret_key,
        algorithm=settings.algorithm,
    )
    assert decode_access_token(token) is None

# Helper functions
def _forged_with_other_key() -> str:
    # Signed with a secret we dont hold
    return jwt.encode({"sub": "alice@test.com"}, "not-the-real-key", algorithm=settings.algorithm)


def _tampered_payload() -> str:
    header, _, signature = create_access_token({"sub": "alice@test.com"}).split(".")
    # Swap in a payload claiming to be someone else, keeping the original signature
    forged_payload = jwt.encode({"sub": "bob@test.com"}, "x", algorithm="HS256").split(".")[1]
    return f"{header}.{forged_payload}.{signature}"


@pytest.mark.parametrize("make_token", [_forged_with_other_key, _tampered_payload])
def test_forged_token_is_rejected(make_token):
    """Ensure a forged token and a tampered payload are rejected."""
    assert decode_access_token(make_token()) is None


def test_token_expires_after_configured_time():
    """Ensure a new token expires after the configured expiry time."""
    before = datetime.now(timezone.utc)
    payload = decode_access_token(create_access_token({"sub": "alice@test.com"}))
    expected = before + timedelta(minutes=settings.access_token_expire_minutes)
    # Allow a few seconds for the time spent creating the token
    assert abs(payload["exp"] - expected.timestamp()) < 5


# Register validation

@pytest.mark.parametrize(
    ("length", "valid"),
    [
        (PASSWORD_MIN_LENGTH - 1, False),  # too short
        (PASSWORD_MIN_LENGTH, True),  # shortest allowed
        (PASSWORD_MAX_LENGTH, True),  # longest allowed
        (PASSWORD_MAX_LENGTH + 1, False),  # too long
    ],
)
def test_register_password_length_limits(length, valid):
    """Ensure passwords within the length limits are accepted and those outside are rejected."""
    if valid:
        RegisterRequest(email="alice@test.com", password="a" * length)
    else:
        with pytest.raises(ValidationError):
            RegisterRequest(email="alice@test.com", password="a" * length)


def test_register_rejects_password_over_72_bytes():
    """Ensure a password over 72 bytes (multi-byte characters such as é count as 2 bytes) is rejected."""
    with pytest.raises(ValidationError):
        RegisterRequest(email="alice@test.com", password="é" * 72)