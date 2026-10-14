from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Travel Cost Optimizer"
    api_v1_prefix: str = "/api/v1"
    cors_origins: list[str] = ["http://localhost:5173"]
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/travel_cost_optimizer"

    class Config:
        env_file = ".env"


settings = Settings()
