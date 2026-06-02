from pathlib import Path
from urllib.parse import quote_plus

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Patent Quote System"
    app_env: str = "local"
    secret_key: str = "change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440

    mysql_host: str = "127.0.0.1"
    mysql_port: int = 3306
    mysql_database: str = "pricing"
    mysql_user: str = "root"
    mysql_password: str = "123456"
    database_url: str | None = None
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    @model_validator(mode="after")
    def build_database_url(self):
        if self.database_url:
            return self

        user = quote_plus(self.mysql_user)
        password = quote_plus(self.mysql_password)
        self.database_url = (
            f"mysql+pymysql://{user}:{password}"
            f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}?charset=utf8mb4"
        )
        return self

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
