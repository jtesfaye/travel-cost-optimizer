from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Roadtrip Planner"
    api_v1_prefix: str = "/api/v1"
    cors_origins: list[str] = ["http://localhost:5173"]
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/roadtrip_planner"
    maps_api_key: str = ""
    places_requests_per_minute: int = 100  # keep below the SearchNearby per-minute quota
    nrel_api_key: str = "DEMO_KEY"  # DEMO_KEY is heavily rate limited; request a real key
    nrel_base_url: str = "https://developer.nlr.gov/api/alt-fuel-stations/v1"

    class Config:
        env_file = ".env"


settings = Settings()
