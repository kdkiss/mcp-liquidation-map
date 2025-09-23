"""Application configuration utilities."""
import os
from typing import Optional


BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DEFAULT_SQLITE_PATH = os.path.join(BASE_DIR, "database", "app.db")


def _str_to_bool(value: Optional[str], default: bool = False) -> bool:
    """Convert common string representations of truthy values to ``bool``.

    Args:
        value: The string value to parse.
        default: The fallback boolean when ``value`` is ``None``.

    Returns:
        ``True`` when ``value`` represents a truthy value, otherwise ``False``.
    """
    if value is None:
        return default

    return value.strip().lower() in {"1", "true", "t", "yes", "y", "on"}


class Config:
    """Base configuration loaded by the Flask application."""

    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
    DEBUG = _str_to_bool(os.getenv("DEBUG"), default=False)
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URI", f"sqlite:///{DEFAULT_SQLITE_PATH}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False


def get_config() -> Config:
    """Return the default :class:`Config` instance."""

    return Config()
