"""Twelve-factor settings with the ASE_ prefix. Every variable is documented in .env.example."""

from __future__ import annotations

import secrets
from enum import StrEnum
from pathlib import Path
from typing import Literal, Self

from pydantic import EmailStr, Field, PrivateAttr, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from ase.application.dto import RateLimits

MIN_SECRET_LENGTH = 32


class Environment(StrEnum):
    DEV = "dev"
    TEST = "test"
    PROD = "prod"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="ASE_", env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    report_pdf_runtime: str | None = Field(default=None, max_length=4096)
    env: Environment = Environment.DEV
    database_url: str = "sqlite+aiosqlite:///./data/ase.db"
    jwt_secret: SecretStr | None = None
    access_token_minutes: int = Field(default=15, ge=1, le=120)
    refresh_token_days: int = Field(default=14, ge=1, le=90)
    cookie_secure: bool | None = None
    public_base_url: str = "http://localhost:5173"
    log_level: str = "INFO"
    smtp_host: str | None = Field(default=None, min_length=1, max_length=253)
    smtp_port: int = Field(default=587, ge=1, le=65535)
    smtp_security: Literal["starttls", "tls"] = "starttls"
    smtp_from_email: EmailStr | None = None
    smtp_username: str | None = Field(default=None, min_length=1, max_length=320)
    smtp_password: SecretStr | None = None
    smtp_timeout_seconds: int = Field(default=10, ge=1, le=30)
    max_request_bytes: int = Field(default=65_536, ge=1_024, le=10_485_760)
    admin_password: SecretStr | None = None
    rate_limit_login_per_ip: int = Field(default=10, ge=1)
    rate_limit_login_per_email: int = Field(default=5, ge=1)
    rate_limit_request_account_per_ip: int = Field(default=3, ge=1)
    rate_limit_forgot_per_ip: int = Field(default=3, ge=1)
    rate_limit_set_password_per_ip: int = Field(default=10, ge=1)
    rate_limit_reports_per_user: int = Field(default=10, ge=1)
    # Feeds: on by default outside tests; polite identification is mandatory for most APIs.
    feeds_enabled: bool | None = None
    feeds_contact: str = "set-ASE_FEEDS_CONTACT@example.invalid"
    conflict_screening_enabled: bool = True
    conflict_screening_calls_per_hour: int = Field(default=6, ge=1, le=30)
    feeds_disabled: str = ""
    satellite_cache_dir: Path = Path("data/celestrak")
    # Fixed monthly baseline. Update only after verifying the next public release.
    ucdp_candidate_version: str = Field(default="26.0.7", pattern=r"^[0-9]{2}\.0\.([1-9]|1[0-2])$")
    ucdp_access_token: SecretStr | None = None
    acled_access_token: SecretStr | None = None
    reliefweb_appname: str | None = Field(
        default=None, pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{1,99}$"
    )
    aisstream_api_key: SecretStr | None = None
    barentswatch_client_id: SecretStr | None = None
    barentswatch_client_secret: SecretStr | None = None
    firms_map_key: SecretStr | None = None
    firms_area: str = Field(default="world", min_length=1, max_length=100)
    live_store_memory_mb: int = Field(default=512, ge=16, le=8_192)
    max_streams_per_user: int = Field(default=4, ge=1, le=64)
    # Wayback Machine snapshots of cited URLs after each report: on by default outside tests.
    archive_enabled: bool | None = None
    alert_webhook_url: str | None = None
    # Ordnance Survey Data Hub key (free OpenData plan). Unset means no OS Maps base layers.
    os_maps_key: SecretStr | None = None
    companies_house_key: SecretStr | None = None
    certificate_transparency_key: SecretStr | None = None
    openalex_api_key: SecretStr | None = None
    openaq_api_key: SecretStr | None = None
    wsdot_access_code: SecretStr | None = None
    ooni_noncommercial_use_acknowledged: bool = False
    uksl_snapshot_path: str | None = None
    ofac_sdn_snapshot_path: str | None = None
    aiddata_catalogue_path: str | None = None
    research_tesseract_path: str | None = None
    research_ffmpeg_path: str | None = None
    research_ffprobe_path: str | None = None
    # Encrypts API keys entered in the admin UI (any string of 32+ characters). Unset means
    # LLM profiles cannot be stored.
    encryption_key: SecretStr | None = None

    _generated_secret: bool = PrivateAttr(default=False)

    @model_validator(mode="after")
    def _finalise(self) -> Self:
        if bool(self.smtp_host) != bool(self.smtp_from_email):
            raise ValueError("Configure ASE_SMTP_HOST and ASE_SMTP_FROM_EMAIL together")
        smtp_password = self.smtp_password.get_secret_value() if self.smtp_password else ""
        if bool(self.smtp_username) != bool(smtp_password):
            raise ValueError("Configure ASE_SMTP_USERNAME and ASE_SMTP_PASSWORD together")
        if self.smtp_username and not self.smtp_host:
            raise ValueError("SMTP credentials require ASE_SMTP_HOST")
        if self.smtp_host and any(char.isspace() for char in self.smtp_host):
            raise ValueError("ASE_SMTP_HOST must not contain whitespace")
        if self.env is Environment.PROD:
            secret = self.jwt_secret.get_secret_value() if self.jwt_secret else ""
            if len(secret) < MIN_SECRET_LENGTH:
                msg = f"ASE_JWT_SECRET must be at least {MIN_SECRET_LENGTH} characters in prod."
                raise ValueError(msg)
        elif self.jwt_secret is None:
            self.jwt_secret = SecretStr(secrets.token_urlsafe(48))
            self._generated_secret = True
        if self.cookie_secure is None:
            self.cookie_secure = self.env is Environment.PROD
        if self.feeds_enabled is None:
            self.feeds_enabled = self.env is not Environment.TEST
        if self.archive_enabled is None:
            self.archive_enabled = self.env is not Environment.TEST
        url = self.alert_webhook_url
        if url is not None and not url.startswith("https://"):
            raise ValueError("ASE_ALERT_WEBHOOK_URL must be an https URL")
        return self

    @property
    def feeds_user_agent(self) -> str:
        return f"TheAllSeeingEye/0.1 (+{self.feeds_contact})"

    @property
    def disabled_feed_ids(self) -> list[str]:
        return [item.strip() for item in self.feeds_disabled.split(",") if item.strip()]

    @property
    def encryption_key_value(self) -> str | None:
        value = self.encryption_key.get_secret_value().strip() if self.encryption_key else ""
        return value or None

    @property
    def os_maps_key_value(self) -> str | None:
        value = self.os_maps_key.get_secret_value().strip() if self.os_maps_key else ""
        return value or None

    @property
    def is_dev(self) -> bool:
        return self.env is Environment.DEV

    @property
    def is_prod(self) -> bool:
        return self.env is Environment.PROD

    @property
    def generated_secret(self) -> bool:
        return self._generated_secret

    @property
    def jwt_secret_value(self) -> str:
        # The validator guarantees a secret exists; this only narrows the type.
        assert self.jwt_secret is not None  # noqa: S101
        return self.jwt_secret.get_secret_value()

    @property
    def rate_limits(self) -> RateLimits:
        return RateLimits(
            login_per_ip=self.rate_limit_login_per_ip,
            login_per_email=self.rate_limit_login_per_email,
            request_account_per_ip=self.rate_limit_request_account_per_ip,
            forgot_per_ip=self.rate_limit_forgot_per_ip,
            set_password_per_ip=self.rate_limit_set_password_per_ip,
            reports_per_user=self.rate_limit_reports_per_user,
        )
