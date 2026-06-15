# Reusable functions injected into route handlers with Depends()
# References: https://fastapi.tiangolo.com/reference/dependencies/

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from backend.auth import decode_access_token
from backend.db import get_db
from backend.models import User

# Get the JWT from the Authorisation header
# References: https://fastapi.tiangolo.com/tutorial/security/simple-oauth2/
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Get the current user from the JWT"""

    # Create an exception for invalid or expired tokens
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )

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

    # Get the user from the database
    user = db.query(User).filter(User.email == email).first()
    # If the user is not found, raise an exception
    if user is None:
        raise credentials_exception

    return user
