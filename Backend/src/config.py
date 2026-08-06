from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "BC06"
    ENVIRONMENT: str = "development"
    SECRET_KEY: str = ""
    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""
    EMBEDDING_MODEL: str = "Qwen/Qwen3-Embedding-8B"
    NATS_URL: str = "nats://localhost:4222"
    HF_TOKEN: str = ""
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
