
from datetime import (
    datetime,
    timedelta,
    timezone,
)

import jwt

from fastapi import Depends, HTTPException
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
)
from jwt import InvalidTokenError
from pwdlib import PasswordHash

from app.config import settings


password_hasher = PasswordHash.recommended()
bearer = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(
    password: str,
    password_hash: str,
) -> bool:
    return password_hasher.verify(
        password,
        password_hash,
    )


def create_access_token(user_id: int) -> str:
    now = datetime.now(timezone.utc)

    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(
            minutes=settings.jwt_expire_minutes
        ),
    }

    return jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


def get_current_user_id(
    credentials: HTTPAuthorizationCredentials | None = (
        Depends(bearer)
    ),
) -> int:
    error = HTTPException(
        status_code=401,
        detail="로그인이 필요하거나 토큰이 유효하지 않습니다.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if credentials is None:
        raise error

    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )

        user_id = int(payload["sub"])

        if user_id <= 0:
            raise error

        return user_id

    except (
        InvalidTokenError,
        KeyError,
        TypeError,
        ValueError,
    ):
        raise error
