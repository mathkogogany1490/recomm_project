
from fastapi import (
    APIRouter,
    Depends,
    status,
)
from sqlalchemy.orm import Session

from app.auth import schema, service
from app.database import get_db
from app.security import get_current_user_id


router = APIRouter(tags=["회원"])


@router.post(
    "/users",
    response_model=schema.UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(
    data: schema.UserCreate,
    db: Session = Depends(get_db),
):
    return service.register(db, data)


@router.post(
    "/auth/verify-email",
    response_model=schema.MessageResponse,
)
def verify_email(
    data: schema.VerifyEmailRequest,
    db: Session = Depends(get_db),
):
    return service.verify_email(db, data)


@router.post(
    "/auth/resend-code",
    response_model=schema.MessageResponse,
)
def resend_code(
    data: schema.ResendCodeRequest,
    db: Session = Depends(get_db),
):
    return service.resend_code(db, data.email)


@router.post(
    "/auth/login",
    response_model=schema.TokenResponse,
)
def login(
    data: schema.LoginRequest,
    db: Session = Depends(get_db),
):
    return service.login(db, data)


@router.get(
    "/users/me",
    response_model=schema.UserResponse,
)
def get_me(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    return service.get_me(db, user_id)
