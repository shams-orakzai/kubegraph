"""Auth endpoints: register, login, me."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from kubegraph.auth.deps import get_current_user
from kubegraph.auth.schemas import (
    ROLES, LoginRequest, RegisterRequest, TokenResponse, UserOut,
)
from kubegraph.auth.security import create_access_token, hash_password, verify_password
from kubegraph.db import get_db
from kubegraph.models.user import User

router = APIRouter(prefix="/auth", tags=["auth"])


def _token_response(user: User) -> TokenResponse:
    return TokenResponse(
        access_token=create_access_token(user.email),
        user=UserOut(id=user.id, name=user.name, email=user.email,
                     org=user.org, role=user.role),
    )


@router.post("/register", response_model=TokenResponse, status_code=201)
def register(body: RegisterRequest, db: Session = Depends(get_db)) -> TokenResponse:
    if db.query(User).filter(User.email == body.email).first():
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")
    role = body.role if body.role in ROLES else "engineer"
    user = User(name=body.name, email=str(body.email), org=body.org, role=role,
                hashed_password=hash_password(body.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return _token_response(user)


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.query(User).filter(User.email == body.email).first()
    if user is None or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")
    return _token_response(user)


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)) -> UserOut:
    return UserOut(id=user.id, name=user.name, email=user.email,
                   org=user.org, role=user.role)
