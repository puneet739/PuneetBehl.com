from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    port: int = 8000
    secret_key: str = "dev-insecure-secret-key-change-me"
    resend_api_key: str = ""
    mail_to: str = "puneet739@gmail.com"
    mail_from: str = "onboarding@resend.dev"
    mail_dry_run: bool = False
    rate_limit_max: int = 5
    rate_limit_window: int = 60
    min_fill_seconds: int = 3
    turnstile_site_key: str = ""
    turnstile_secret: str = ""
    trusted_hosts: str = "*"

    @property
    def dry_run(self) -> bool:
        return self.mail_dry_run or not self.resend_api_key


@lru_cache
def get_settings() -> Settings:
    return Settings()
