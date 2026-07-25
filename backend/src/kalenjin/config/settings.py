from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class GarminConfig(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    garmin_email: str
    garmin_password: str
    garmin_tokenstore: str = str(Path.home() / ".kalenjin" / "garmin_tokens")


class DbConfig(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str


class LlmConfig(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    gemini_api_key: str
