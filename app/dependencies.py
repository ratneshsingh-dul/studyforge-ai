from typing import Annotated

from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.security import read_access_token


def get_current_user(
    session_token: Annotated[str | None, Cookie()] = None,
    db: Session = Depends(get_db),
) -> User:
    if not session_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sign in to continue")

    user_id = read_access_token(session_token)
    user = db.get(User, user_id) if user_id is not None else None
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session is invalid or expired")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
