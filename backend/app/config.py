from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite:///./autopaperreader.db"
    openai_base_url: str = "https://api.openai.com/v1"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    openai_temperature: float = 0.2
    app_env: str = "development"
    analysis_max_text_chars: int = Field(default=60000, ge=1000, le=500000)
    schedule_hour: int = Field(default=11, ge=0, le=23)
    arxiv_max_results: int = Field(default=30, ge=1, le=100)
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    admin_password: str = ""
    session_secret: str = "change-me-session-secret"
    session_cookie_name: str = "apr_session"
    session_max_age_seconds: int = 60 * 60 * 24 * 7
    session_cookie_secure: bool = False
    pdf_max_bytes: int = Field(default=25 * 1024 * 1024, ge=1024, le=100 * 1024 * 1024)
    pdf_max_pages: int = Field(default=100, ge=1, le=1000)
    external_timeout_seconds: float = Field(default=30, gt=0, le=120)
    worker_poll_seconds: float = Field(default=1, gt=0, le=60)

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @field_validator("cors_origins")
    @classmethod
    def validate_origins(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("CORS_ORIGINS cannot be empty")
        return value

    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
