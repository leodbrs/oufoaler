from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    host: str = "0.0.0.0"
    port: int = 8000
    logging_level: str = Field("INFO")
    openrouteservice_api_key: str = Field(...)
    chargetrip_client_id: str = Field(...)
    chargetrip_app_id: str = Field(...)

    model_config = SettingsConfigDict(
        env_prefix="OUFOALER_", case_sensitive=False, extra="forbid"
    )
