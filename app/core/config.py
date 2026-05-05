from pydantic import BaseModel
import os


class Settings(BaseModel):
    api_v1_prefix: str = "/api/v1"
    app_name: str = "Research Platform API"
    cors_origins: list[str] = ["*"]
    access_token_algorithm: str = "HS256"


def get_settings() -> Settings:
    prefix = os.getenv("API_V1_PREFIX", "/api/v1")
    return Settings(api_v1_prefix=prefix)

