from pydantic_settings import BaseSettings, SettingsConfigDict

MIN_POLL_INTERVAL_SECONDS = 15

# AbuseIPDB's free-tier /blacklist endpoint is capped at 5 requests/day
# (confirmed via a live 429 response: "Daily rate limit of 5 requests
# exceeded for this endpoint"). This is far stricter than /check's 1,000/day
# quota. A hard-coded floor here (independent of the DB-backed quota guard
# in app.scheduler) so a misconfigured .env can't accidentally burn the
# day's blacklist calls in minutes, per Security & Access doc section 5.
MIN_BLACKLIST_POLL_INTERVAL_SECONDS = 4 * 3600
BLACKLIST_DAILY_SAFE_MAX = 4  # stay under the real cap of 5, one held in reserve


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    abuseipdb_api_key: str = ""
    cloudflare_radar_api_token: str = ""
    ipinfo_api_key: str = ""
    ip_hash_salt: str = ""
    ingest_poll_interval_seconds: int = 30
    blacklist_poll_interval_seconds: int = 6 * 3600
    # Free-tier per-call cap for /blacklist is unverified as of this writing
    # (quota was exhausted mid-verification) — 1000 is a conservative
    # placeholder, not a confirmed API limit. Re-check via a live call
    # before relying on a larger number.
    blacklist_fetch_limit: int = 1000
    cors_allowed_origins: str = "http://localhost:5173"
    database_url: str = "sqlite:///./cyberpulse.db"
    environment: str = "development"

    @property
    def poll_interval_seconds(self) -> int:
        return max(self.ingest_poll_interval_seconds, MIN_POLL_INTERVAL_SECONDS)

    @property
    def blacklist_poll_seconds(self) -> int:
        return max(self.blacklist_poll_interval_seconds, MIN_BLACKLIST_POLL_INTERVAL_SECONDS)

    @property
    def cors_origins(self) -> list[str]:
        if self.environment != "production":
            return ["*"]
        return [origin.strip() for origin in self.cors_allowed_origins.split(",") if origin.strip()]


settings = Settings()
