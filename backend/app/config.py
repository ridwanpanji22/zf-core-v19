from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Database
    DB_HOST: str = "db"
    DB_PORT: int = 5432
    DB_NAME: str = "zfcore"
    DB_USER: str = "zfcore"
    DB_PASSWORD: str = "changeme"

    # Redis
    REDIS_URL: str = "redis://redis:6379/0"

    # OKX API
    OKX_API_KEY: str = ""
    OKX_SECRET_KEY: str = ""
    OKX_PASSPHRASE: str = ""

    # Google OAuth 2.0
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "https://zf.yourdomain.com/api/auth/google/callback"

    # Super Admin
    SUPER_ADMIN_EMAIL: str = "admin@example.com"

    # API Key Encryption
    API_KEY_ENCRYPTION_SECRET: str = "changeme-32-byte-random-string"

    # Telegram
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_CHAT_ID: str = ""

    # Auth
    JWT_SECRET: str = "changeme-to-random-string"
    JWT_ACCESS_EXPIRE_MINUTES: int = 60
    JWT_REFRESH_EXPIRE_DAYS: int = 7

    # App
    APP_ENV: str = "production"
    LOG_LEVEL: str = "INFO"
    ASSET_SWARM_SIZE: int = 200
    DEMO_ENABLED: bool = True
    DEMO_INITIAL_BALANCE: float = 10000.0
    DEMO_MAX_LEVERAGE: int = 10

    @property
    def database_url(self) -> str:
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

settings = Settings()
