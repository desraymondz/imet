# Reusable functions injected into route handlers with Depends()
# References: https://fastapi.tiangolo.com/reference/dependencies/

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.auth import ACCESS_COOKIE_NAME, decode_access_token, normalise_email
from backend.db import get_db
from backend.models import User

# Get the JWT from the Authorisation header
# References: https://fastapi.tiangolo.com/tutorial/security/simple-oauth2/
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


def find_user_by_email(db: Session, email: str) -> User | None:
    """Look up a user by email."""
    normalised = normalise_email(email)
    if not normalised:
        return None
    return db.query(User).filter(func.lower(User.email) == normalised).first()


def get_current_user(
    request: Request,
    bearer_token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Get the current user from the HTTP-only cookie, or a Bearer token (Swagger /docs)."""

    # Create an exception for invalid or expired tokens
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Use the cookie (browser session) if available and fall back to Bearer for /docs
    token = request.cookies.get(ACCESS_COOKIE_NAME) or bearer_token
    if not token:
        raise credentials_exception

    # Decode the JWT and get the payload
    payload = decode_access_token(token)
    # If the token is invalid, raise an exception
    if payload is None:
        raise credentials_exception

    # Get the email from the payload
    email: str | None = payload.get("sub")
    # If the email is not found, raise an exception
    if email is None:
        raise credentials_exception

    # Get the user from the database (case-insensitive, matches register/login)
    user = find_user_by_email(db, email)
    # If the user is not found, raise an exception
    if user is None:
        raise credentials_exception

    return user