"""Application configuration helpers."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Type


class BaseConfig:
    """Base configuration shared across environments."""

    PROJECT_ROOT = Path(__file__).resolve().parent.parent
    SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "dev-secret-change-me")
    DATABASE_URL = os.getenv("DATABASE_URL") or f"sqlite:///{PROJECT_ROOT / 'campus_resource_hub.db'}"
    UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", str(PROJECT_ROOT / "uploads"))
    MAX_CONTENT_LENGTH = 2 * 1024 * 1024  # 2 MB
    WTF_CSRF_ENABLED = True
    SESSION_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_HTTPONLY = True
    PREFERRED_URL_SCHEME = "https"


class DevelopmentConfig(BaseConfig):
    """Configuration tweaks for local development."""

    DEBUG = True
    TESTING = False


class TestingConfig(BaseConfig):
    """In-memory database configuration for pytest."""

    DEBUG = False
    TESTING = True
    DATABASE_URL = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False


class ProductionConfig(BaseConfig):
    """Production hardened configuration."""

    DEBUG = False
    TESTING = False


def get_config() -> Type[BaseConfig]:
    """Return the configuration class based on FLASK_ENV."""

    env = os.getenv("FLASK_ENV", "development").lower()
    if env == "production":
        return ProductionConfig
    if env == "testing":
        return TestingConfig
    return DevelopmentConfig

