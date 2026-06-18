# Configuration for the application

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration for the application"""
    # Load environments variables
    model_config = SettingsConfigDict(env_file=".env.local", extra="ignore")

    database_url: str
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    debug: bool = False

    ollama_host: str
    ollama_model_fast: str
    ollama_model_quality: str

@lru_cache
def get_settings() -> Settings:
    """Cache the settings instance."""
    return Settings()


# Set settings as an object to be used throughout the application
settings: Settings = get_settings()