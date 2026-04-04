from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://user:password@localhost/dbname"
    ANTHROPIC_API_KEY: str = ""
    FINNHUB_API_KEY: str = ""

    class Config:
        env_file = ".env"


settings = Settings()
