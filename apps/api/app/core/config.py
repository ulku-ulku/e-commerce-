from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Docker'da .env postgres URL'i verir; yerelde varsayılan SQLite (kurulum gerektirmez)
    DATABASE_URL: str = "sqlite:///./commerce_ai.db"
    REDIS_URL: str = "redis://redis:6379/0"

    JWT_SECRET: str = "dev-secret"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 1440

    # Sağlayıcı-bağımsız LLM (OpenAI-uyumlu uç nokta). Anahtar yoksa deterministik fallback çalışır.
    LLM_API_KEY: str = ""
    LLM_BASE_URL: str = "https://api.openai.com/v1"
    LLM_MODEL: str = "gpt-4o-mini"


settings = Settings()
