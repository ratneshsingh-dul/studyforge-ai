from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.dependencies import CurrentUser
from app.models import User
from app.schemas import Credentials, UserPublic
from app.security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["authentication"])
DbSession = Annotated[Session, Depends(get_db)]


def set_session_cookie(response: Response, user: User) -> None:
    settings = get_settings()
    response.set_cookie(
        key="session_token",
        value=create_access_token(user.id),
        max_age=settings.access_token_minutes * 60,
        httponly=True,
        secure=settings.secure_cookies,
        samesite="lax",
        path="/",
    )


@router.post("/register", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
def register(credentials: Credentials, response: Response, db: DbSession) -> User:
    email = str(credentials.email).strip().lower()
    existing = db.scalar(select(User).where(User.email == email))
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="An account with this email already exists")

    user = User(email=email, password_hash=hash_password(credentials.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    set_session_cookie(response, user)
    return user


@router.post("/login", response_model=UserPublic)
def login(credentials: Credentials, response: Response, db: DbSession) -> User:
    email = str(credentials.email).strip().lower()
    user = db.scalar(select(User).where(User.email == email))
    if user is None or not verify_password(credentials.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Email or password is incorrect")
    set_session_cookie(response, user)
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response) -> Response:
    response.delete_cookie("session_token", path="/", samesite="lax")
    return response


@router.get("/me", response_model=UserPublic)
def me(user: CurrentUser) -> User:
    return user
