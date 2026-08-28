"""Current-user dependency: validates the Bearer token and loads the user."""

from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from kubegraph.auth.security import decode_token
from kubegraph.db import get_db
from kubegraph.models.user import User

bearer = HTTPBearer(auto_error=False)

_UNAUTH = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Not authenticated",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    if creds is None or not creds.credentials:
        raise _UNAUTH
    email = decode_token(creds.credentials)
    if email is None:
        raise _UNAUTH
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise _UNAUTH
    return user
