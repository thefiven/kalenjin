from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    garmin_email: str
    garmin_password: str
    database_url: str
    garmin_tokenstore: str = str(Path.home() / ".kalenjin" / "garmin_tokens")
