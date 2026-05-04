from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql://octane:octane@localhost:5432/octane"
    cors_origins: str = "http://localhost:5173"
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_pass: str = ""
    alert_from_email: str = "alerts@octane.lk"
    site_url: str = "https://octane.lk"
    scraper_user_agent: str = "OctaneBot/1.0 (+https://octane.lk)"
    admin_email: str = ""
    rate_limit: str = "60/minute"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
