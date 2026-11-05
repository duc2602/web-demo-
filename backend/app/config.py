"""Application configuration, loaded from environment variables / .env file."""

import ipaddress
from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BASE_DIR / ".env", env_file_encoding="utf-8", extra="ignore")

    # Local server binding
    app_host: str = Field(min_length=1)
    app_port: int = Field(gt=0, le=65535)
    tls_certfile: str | None = None
    tls_keyfile: str | None = Field(default=None, repr=False)
    tls_terminated_by_proxy: bool = False

    # Directories (relative to backend/ root, or absolute)
    models_dir: str
    uploads_dir: str
    outputs_dir: str

    # Upload limits
    max_model_size_mb: int = Field(gt=0)
    max_image_size_mb: int = Field(gt=0)

    # Inference defaults
    default_tile_size: int = Field(gt=0)
    default_tile_overlap: int = Field(ge=0)
    default_batch_size: int = Field(gt=0)
    default_device: Literal["auto", "cpu", "cuda"]
    default_processing_mode: Literal["tile", "full_image"]

    # Frontend security
    frontend_origin: str
    cors_allowed_origins: str

    # Authentication security
    session_cookie_name: str
    session_ttl_seconds: int = Field(gt=0)
    session_cookie_secure: bool
    session_cookie_samesite: Literal["lax", "strict", "none"]
    min_password_length: int = Field(ge=10, le=128)
    max_password_length: int = Field(ge=10, le=128)
    allow_public_registration: bool
    initial_admin_setup_key: str | None = Field(default=None, min_length=32, max_length=256, repr=False)
    account_recovery_key: str | None = Field(default=None, min_length=32, max_length=256, repr=False)

    # MySQL connection; password is required and excluded from repr output.
    mysql_host: str
    mysql_port: int = Field(gt=0, le=65535)
    mysql_user: str
    mysql_password: str = Field(repr=False, min_length=1)
    mysql_database: str
    mysql_ssl_ca: str | None = None

    @model_validator(mode="after")
    def validate_transport_security(self) -> "Settings":
        if bool(self.tls_certfile) != bool(self.tls_keyfile):
            raise ValueError("TLS_CERTFILE and TLS_KEYFILE must be configured together.")
        if self.tls_certfile and not self.session_cookie_secure:
            raise ValueError("SESSION_COOKIE_SECURE must be true when backend TLS is enabled.")
        if self.tls_terminated_by_proxy and not self.session_cookie_secure:
            raise ValueError("SESSION_COOKIE_SECURE must be true when TLS is terminated by a trusted proxy.")

        app_host = self.app_host.strip().lower()
        app_is_loopback = app_host == "localhost"
        if not app_is_loopback:
            try:
                app_is_loopback = ipaddress.ip_address(app_host).is_loopback
            except ValueError:
                app_is_loopback = False
        if not app_is_loopback and not self.tls_certfile and not self.tls_terminated_by_proxy:
            raise ValueError(
                "Configure TLS_CERTFILE and TLS_KEYFILE, or set TLS_TERMINATED_BY_PROXY=true "
                "when the hosting platform provides trusted HTTPS."
            )

        if self.tls_certfile:
            for name, value in (("TLS_CERTFILE", self.tls_certfile), ("TLS_KEYFILE", self.tls_keyfile)):
                if not self._resolve_backend_path(value).is_file():
                    raise ValueError(f"{name} does not point to an existing file.")

        host = self.mysql_host.strip().lower()
        is_loopback = host == "localhost"
        if not is_loopback:
            try:
                is_loopback = ipaddress.ip_address(host).is_loopback
            except ValueError:
                is_loopback = False
        if not is_loopback and not self.mysql_ssl_ca:
            raise ValueError("MYSQL_SSL_CA is required when MySQL is not on localhost.")
        if self.mysql_ssl_ca and not self._resolve_backend_path(self.mysql_ssl_ca).is_file():
            raise ValueError("MYSQL_SSL_CA does not point to an existing CA certificate file.")
        return self

    @staticmethod
    def _resolve_backend_path(value: str | None) -> Path:
        path = Path(value or "")
        return path if path.is_absolute() else BASE_DIR / path

    @property
    def tls_cert_path(self) -> Path | None:
        return self._resolve_backend_path(self.tls_certfile) if self.tls_certfile else None

    @property
    def tls_key_path(self) -> Path | None:
        return self._resolve_backend_path(self.tls_keyfile) if self.tls_keyfile else None

    @property
    def mysql_ssl_ca_path(self) -> Path | None:
        return self._resolve_backend_path(self.mysql_ssl_ca) if self.mysql_ssl_ca else None

    @property
    def cors_origins(self) -> list[str]:
        extra_origins = [origin.strip() for origin in self.cors_allowed_origins.split(",") if origin.strip()]
        return list(dict.fromkeys([self.frontend_origin, *extra_origins]))

    @property
    def models_path(self) -> Path:
        p = BASE_DIR / self.models_dir
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def uploads_path(self) -> Path:
        p = BASE_DIR / self.uploads_dir
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def outputs_path(self) -> Path:
        p = BASE_DIR / self.outputs_dir
        p.mkdir(parents=True, exist_ok=True)
        return p


settings = Settings()
