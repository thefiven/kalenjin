from pydantic_settings import BaseSettings, SettingsConfigDict


class DbConfig(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str


class EncryptionConfig(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    secret_encryption_key: str


class AuthConfig(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    google_client_id: str
    google_client_secret: str
    google_oauth_redirect_uri: str
    session_secret_key: str
    frontend_base_url: str = "http://localhost:3000"
