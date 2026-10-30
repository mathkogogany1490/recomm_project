
import secrets
import smtplib

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.auth import repository
from app.auth.schema import (
    LoginRequest,
    UserCreate,
    VerifyEmailRequest,
)
from app.security import (
    create_access_token,
    hash_password,
    verify_password,
)


def normalize_email(email: str):
    return email.strip().lower()


def issue_code(email: str):
    result, reservation = (
        repository.reserve_email_send(email)
    )

    if result == -1:
        raise HTTPException(
            429,
            "60초 후 다시 요청하세요.",
        )

    if result == -2:
        raise HTTPException(
            429,
            "최근 1시간 최대 5회 발송할 수 있습니다.",
        )

    code = f"{secrets.randbelow(1000000):06d}"

    try:
        repository.store_code(email, code)
        repository.send_email(email, code)

    except (OSError, smtplib.SMTPException):
        repository.release_email_send(
            email,
            reservation,
        )

        raise HTTPException(
            503,
            "이메일 발송에 실패했습니다.",
        )


def register(db: Session, data: UserCreate):
    email = normalize_email(data.email)

    if repository.get_by_email(db, email):
        raise HTTPException(
            409,
            "이미 가입된 이메일입니다.",
        )

    user = repository.create_user(
        db,
        email,
        hash_password(data.password),
    )

    if user is None:
        raise HTTPException(
            409,
            "이미 가입된 이메일입니다.",
        )

    issue_code(email)

    return user


def verify_email(
    db: Session,
    data: VerifyEmailRequest,
):
    email = normalize_email(data.email)

    user = repository.get_by_email(
        db,
        email,
    )

    if user is None:
        raise HTTPException(
            404,
            "회원이 존재하지 않습니다.",
        )

    if user.is_verified:
        raise HTTPException(
            409,
            "이미 인증된 회원입니다.",
        )

    result = repository.check_code(
        email,
        data.code,
    )

    if result == -1:
        raise HTTPException(
            400,
            "인증번호가 없거나 만료되었습니다.",
        )

    if result == -2:
        raise HTTPException(
            429,
            "인증번호 확인 5회를 초과했습니다.",
        )

    if result == 0:
        raise HTTPException(
            400,
            "인증번호가 일치하지 않습니다.",
        )

    repository.mark_verified(db, user)

    return {
        "message": "이메일 인증이 완료되었습니다."
    }


def resend_code(db: Session, email: str):
    email = normalize_email(email)

    user = repository.get_by_email(
        db,
        email,
    )

    if user is None:
        raise HTTPException(
            404,
            "회원이 존재하지 않습니다.",
        )

    if user.is_verified:
        raise HTTPException(
            409,
            "이미 인증된 회원입니다.",
        )

    issue_code(email)

    return {
        "message": "인증번호를 다시 보냈습니다."
    }


def login(db: Session, data: LoginRequest):
    email = normalize_email(data.email)

    user = repository.get_by_email(
        db,
        email,
    )

    if user is None or not verify_password(
        data.password,
        user.password_hash,
    ):
        raise HTTPException(
            401,
            "이메일 또는 비밀번호가 올바르지 않습니다.",
        )

    if not user.is_verified:
        raise HTTPException(
            403,
            "이메일 인증이 필요합니다.",
        )

    return {
        "access_token": create_access_token(user.id),
        "token_type": "bearer",
    }


def get_me(db: Session, user_id: int):
    user = repository.get_by_id(
        db,
        user_id,
    )

    if user is None:
        raise HTTPException(
            401,
            "유효하지 않은 회원입니다.",
        )

    if not user.is_verified:
        raise HTTPException(
            403,
            "이메일 인증이 필요합니다.",
        )

    return user
