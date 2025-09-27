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

    SECRET_KEY = os.getenv("SECRET_KEY")
    DEBUG = _str_to_bool(os.getenv("DEBUG"), default=False)
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URI", f"sqlite:///{DEFAULT_SQLITE_PATH}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    ENABLE_USER_API = _str_to_bool(os.getenv("ENABLE_USER_API"), default=False)


def get_config() -> Config:
    """Return the default :class:`Config` instance.

    Ensures that a ``SECRET_KEY`` is provided when ``DEBUG`` is disabled so
    deployments fail fast with a clear error instead of silently running with a
    weak default secret.
    """

    config = Config()

    if not config.SECRET_KEY:
        if config.DEBUG:
            config.SECRET_KEY = "dev-secret-key"
        else:
            raise RuntimeError(
                "SECRET_KEY environment variable must be set when DEBUG is False"
            )

    return config
