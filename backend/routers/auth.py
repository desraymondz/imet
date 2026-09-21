from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from backend.auth import (
    clear_auth_cookie,
    create_access_token,
    hash_password,
    set_auth_cookie,
    verify_password,
)
from backend.db import get_db
from backend.dependencies import get_current_user
from backend.models import User
from backend.schemas import RegisterRequest, UserOut

# Define the prefix and tags for the auth router
router = APIRouter(prefix="/auth", tags=["auth"])


def _issue_session(response: Response, email: str) -> dict[str, str]:
    """
    Called after a successful login:
    - Create a JWT
    - Store it in an HTTP-only cookie and sends it on later /api/* calls
    - Return it for /docs Bearer auth
    """
    token = create_access_token({"sub": email})
    set_auth_cookie(response, token)
    return {
        "access_token": token,
        "token_type": "bearer",
    }


@router.post("/login")
def login(
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """
    Login a user with email and password.
    Sets an HTTP-only cookie and returns an access token if successful,
    otherwise raises a 401 Unauthorised exception.
    """
    # Look up user by email
    existing_user = db.query(User).filter(User.email == form_data.username).first()

    # If the user is not found or the password is incorrect, raise an exception
    if not existing_user or not verify_password(form_data.password, existing_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return _issue_session(response, existing_user.email)


@router.post("/register")
def register(
    body: RegisterRequest,
    response: Response,
    db: Session = Depends(get_db),
):
    """
    Register a new user with email and password.
    Sets an HTTP-only cookie and returns an access token if successful,
    otherwise raises a 400 Bad Request exception.
    """
    # Check if the email is already taken
    existing_email = db.query(User).filter(User.email == body.email).first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Create a new user
    new_user = User(
        email=body.email,
        hashed_password=hash_password(body.password),
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return _issue_session(response, new_user.email)


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    """Return the current user if the session cookie (or Bearer token) is valid."""
    return current_user


@router.post("/logout")
def logout(response: Response):
    """Clear the auth cookie."""
    clear_auth_cookie(response)
    return {"ok": True}