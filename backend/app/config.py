from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration, read from environment variables (or a local .env file)."""

    app_name: str = "StayDesk API"
    app_version: str = "1.0.0"
    # Injected at image build time / by Helm so a running pod can be traced back to a commit.
    git_sha: str = "dev"
    database_url: str = "postgresql+psycopg://staydesk:staydesk@localhost:5432/staydesk"
    # The hotel's local timezone decides what "today" means for arrivals and departures.
    hotel_timezone: str = "Asia/Kolkata"
    # Only needed when the UI is served from a different origin (e.g. `npm run dev` without proxy).
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
