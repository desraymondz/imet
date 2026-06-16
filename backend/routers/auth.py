from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from backend.auth import create_access_token, verify_password
from backend.db import get_db
from backend.models import User

# Define the prefix and tags for the auth router
router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login")
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """
    Login a user with email and password.
    Returns an access token if successful, otherwise raises a 401 Unauthorized exception.
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

    # Create an access token for the user
    token = create_access_token({"sub": existing_user.email})
    return {
        "access_token": token,
        "token_type": "bearer"
    }


@router.post("/register")
def register(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """
    Register a new user with email and password.
    Returns an access token if successful, otherwise raises a 400 Bad Request exception.
    """
    from backend.auth import hash_password

    # Check if the email is already taken
    existing_email = db.query(User).filter(User.email == form_data.username).first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Create a new user
    new_user = User(
        email=form_data.username,
        hashed_password=hash_password(form_data.password),
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Create an access token for the user
    token = create_access_token({"sub": new_user.email})
    return {
        "access_token": token,
        "token_type": "bearer"
    }