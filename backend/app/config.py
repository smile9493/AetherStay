from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(_ENV_FILE, ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_NAME: str = "AetherStay"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = True

    DATABASE_URL: str = "mysql+aiomysql://aetherstay:aetherstay@localhost:3306/aetherstay"

    SECRET_KEY: str = "change-me-in-production-use-a-long-random-string"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # 生产环境置为 True，让 Cookie 仅通过 HTTPS 传输（CSRF 防护的一部分）
    COOKIE_SECURE: bool = False

    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    HOLD_TTL_MINUTES: int = 15
    HOLD_RELEASE_INTERVAL_MINUTES: int = 1
    AUTO_CHECKOUT_INTERVAL_MINUTES: int = 1

    # 并发预订悲观锁 NOWAIT 失败后的重试退避
    BOOKING_LOCK_RETRY_TIMES: int = 3
    BOOKING_LOCK_RETRY_BASE_MS: int = 50

    # AI Agent（OpenAI 兼容协议，默认 DeepSeek）
    LLM_API_KEY: str = ""
    LLM_BASE_URL: str = "https://api.deepseek.com"
    LLM_MODEL: str = "deepseek-chat"
    LLM_TEMPERATURE: float = 0.3
    LLM_TIMEOUT_SECONDS: float = 120.0
    LLM_MAX_TOOL_ITERATIONS: int = 5

    # Agent/MCP 工具调用限流（滑动窗口）
    AGENT_RATE_LIMIT_MAX: int = 30
    AGENT_RATE_LIMIT_WINDOW_SECONDS: int = 60


@lru_cache
def get_settings() -> Settings:
    return Settings()
