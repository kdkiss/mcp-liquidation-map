"""Core package for the MCP liquidation map service."""

from __future__ import annotations

from typing import Any

from .config import Config  # re-export for convenience

__all__ = ["Config", "app", "create_server"]


def __getattr__(name: str) -> Any:
    """Lazily expose heavy submodules on first access."""

    if name == "app":
        from .main import app as flask_app

        return flask_app
    if name == "create_server":
        from .server import create_server as factory

        return factory
    raise AttributeError(name)
