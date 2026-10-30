
from pathlib import Path

from pydantic import computed_field
from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict,
)
from sqlalchemy.engine import URL


ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    app_name: str = "추천 시스템 프로젝트"

    postgres_user: str
    postgres_password: str
    postgres_db: str
    postgres_host: str = "localhost"
    postgres_port: int = 54321

    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0

    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60

    gmail_address: str
    gmail_app_password: str

    frontend_origin: str = "http://localhost:5173"

    email_code_expire_seconds: int = 300
    email_code_max_attempts: int = 5
    email_resend_interval_seconds: int = 60
    email_hourly_limit: int = 5

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def database_url(self):
        return URL.create(
            drivername="postgresql+psycopg",
            username=self.postgres_user,
            password=self.postgres_password,
            host=self.postgres_host,
            port=self.postgres_port,
            database=self.postgres_db,
        )

    @property
    def redis_url(self):
        return (
            f"redis://{self.redis_host}:"
            f"{self.redis_port}/{self.redis_db}"
        )


settings = Settings()
