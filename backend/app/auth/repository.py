
import hashlib
import hmac
import html
import secrets
import smtplib
import time

from email.message import EmailMessage

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.model import User
from app.config import settings
from app.redis_client import redis_client


# 인증번호 확인과 삭제를 원자적으로 처리
VERIFY_SCRIPT = """
local code = redis.call('GET', KEYS[1])

if not code then
    return -1
end

local attempts = tonumber(
    redis.call('GET', KEYS[2]) or '0'
)

if attempts >= tonumber(ARGV[2]) then
    redis.call('DEL', KEYS[1], KEYS[2])
    return -2
end

if code == ARGV[1] then
    redis.call('DEL', KEYS[1], KEYS[2])
    return 1
end

attempts = redis.call('INCR', KEYS[2])

if attempts >= tonumber(ARGV[2]) then
    redis.call('DEL', KEYS[1], KEYS[2])
    return -2
end

return 0
"""


# 60초 간격 및 최근 1시간 최대 5회
RATE_SCRIPT = """
redis.call(
    'ZREMRANGEBYSCORE',
    KEYS[2],
    '-inf',
    tonumber(ARGV[1]) - 3600
)

if redis.call('EXISTS', KEYS[1]) == 1 then
    return -1
end

if redis.call('ZCARD', KEYS[2])
    >= tonumber(ARGV[3]) then
    return -2
end

redis.call(
    'SET',
    KEYS[1],
    ARGV[4],
    'EX',
    ARGV[2]
)

redis.call(
    'ZADD',
    KEYS[2],
    ARGV[1],
    ARGV[4]
)

redis.call('EXPIRE', KEYS[2], 3700)

return 1
"""


# 메일 발송 실패 시 자기 예약만 취소
RELEASE_SCRIPT = """
if redis.call('GET', KEYS[1]) == ARGV[1] then
    redis.call('DEL', KEYS[1])
end

redis.call('ZREM', KEYS[2], ARGV[1])

return 1
"""


def get_by_email(db: Session, email: str):
    return db.scalar(
        select(User).where(User.email == email)
    )


def get_by_id(db: Session, user_id: int):
    return db.get(User, user_id)


def create_user(
    db: Session,
    email: str,
    password_hash: str,
):
    user = User(
        email=email,
        password_hash=password_hash,
    )

    db.add(user)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return None

    db.refresh(user)
    return user


def mark_verified(db: Session, user: User):
    user.is_verified = True
    db.commit()
    db.refresh(user)
    return user


def _keys(email: str):
    identity = hashlib.sha256(
        email.encode()
    ).hexdigest()

    return {
        "code": f"verify:code:{identity}",
        "attempts": f"verify:attempts:{identity}",
        "cooldown": f"verify:cooldown:{identity}",
        "hour": f"verify:hour:{identity}",
    }


def _digest(email: str, code: str):
    return hmac.new(
        settings.jwt_secret_key.encode(),
        f"{email}:{code}".encode(),
        hashlib.sha256,
    ).hexdigest()


def reserve_email_send(email: str):
    keys = _keys(email)
    reservation = secrets.token_hex(16)

    result = redis_client.eval(
        RATE_SCRIPT,
        2,
        keys["cooldown"],
        keys["hour"],
        time.time(),
        settings.email_resend_interval_seconds,
        settings.email_hourly_limit,
        reservation,
    )

    return result, reservation


def release_email_send(
    email: str,
    reservation: str,
):
    keys = _keys(email)

    redis_client.eval(
        RELEASE_SCRIPT,
        2,
        keys["cooldown"],
        keys["hour"],
        reservation,
    )


def store_code(email: str, code: str):
    keys = _keys(email)

    pipe = redis_client.pipeline(transaction=True)

    pipe.set(
        keys["code"],
        _digest(email, code),
        ex=settings.email_code_expire_seconds,
    )

    pipe.set(
        keys["attempts"],
        0,
        ex=settings.email_code_expire_seconds,
    )

    pipe.execute()


def check_code(email: str, code: str):
    keys = _keys(email)

    return redis_client.eval(
        VERIFY_SCRIPT,
        2,
        keys["code"],
        keys["attempts"],
        _digest(email, code),
        settings.email_code_max_attempts,
    )


def send_email(email: str, code: str):
    safe_code = html.escape(code)

    html_body = f"""
    <!DOCTYPE html>
    <html lang="ko">
    <body style="
        margin:0;
        padding:40px 16px;
        background:#f1f5f9;
        font-family:Arial,sans-serif;
    ">
      <div style="
        max-width:440px;
        margin:auto;
        padding:32px;
        background:#ffffff;
        border-radius:18px;
        text-align:center;
        box-shadow:0 8px 24px #00000012;
      ">
        <h2 style="color:#1e293b;">
          추천 시스템 프로젝트
        </h2>

        <p style="color:#64748b;">
          이메일 인증번호를 입력해 주세요.
        </p>

        <div style="
          margin:24px 0;
          padding:22px;
          border-radius:12px;
          background:#eef2ff;
          color:#4338ca;
          font-size:36px;
          font-weight:bold;
          letter-spacing:7px;
        ">
          {safe_code}
        </div>

        <p style="color:#475569;">
          인증번호는 5분 동안 유효합니다.
        </p>

        <p style="font-size:12px;color:#94a3b8;">
          요청하지 않았다면 무시해 주세요.
        </p>
      </div>
    </body>
    </html>
    """

    message = EmailMessage()

    message["Subject"] = "추천 시스템 이메일 인증"
    message["From"] = settings.gmail_address
    message["To"] = email

    message.set_content(
        f"인증번호: {code}\n유효시간: 5분"
    )

    message.add_alternative(
        html_body,
        subtype="html",
    )

    with smtplib.SMTP_SSL(
        "smtp.gmail.com",
        465,
        timeout=15,
    ) as smtp:
        smtp.login(
            settings.gmail_address,
            settings.gmail_app_password.replace(" ", ""),
        )

        smtp.send_message(message)
