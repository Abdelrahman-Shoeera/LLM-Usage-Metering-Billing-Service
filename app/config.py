from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str

    STRIPE_SECRET_KEY: str = ""
    STRIPE_PUBLISHABLE_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""

    APP_ENV: str = "development"

    class Config:
        env_file = ".env"


settings = Settings()