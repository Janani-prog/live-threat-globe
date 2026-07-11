from pydantic_settings import BaseSettings, SettingsConfigDict

MIN_POLL_INTERVAL_SECONDS = 15


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    abuseipdb_api_key: str = ""
    cloudflare_radar_api_token: str = ""
    ipinfo_api_key: str = ""
    ip_hash_salt: str = ""
    ingest_poll_interval_seconds: int = 30
    cors_allowed_origins: str = "http://localhost:5173"
    database_url: str = "sqlite:///./cyberpulse.db"
    environment: str = "development"

    @property
    def poll_interval_seconds(self) -> int:
        return max(self.ingest_poll_interval_seconds, MIN_POLL_INTERVAL_SECONDS)

    @property
    def cors_origins(self) -> list[str]:
        if self.environment != "production":
            return ["*"]
        return [origin.strip() for origin in self.cors_allowed_origins.split(",") if origin.strip()]


settings = Settings()
