"""Tests for the configuration helper utilities."""

import importlib.util
from pathlib import Path

import pytest


def load_config_module(module_name: str = "test_config_module"):
    """Load ``mcp_liquidation_map.config`` under an isolated module name."""

    config_path = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "mcp_liquidation_map"
        / "config.py"
    )
    spec = importlib.util.spec_from_file_location(module_name, config_path)
    if spec is None or spec.loader is None:  # pragma: no cover - defensive
        raise RuntimeError("Unable to load config module for testing")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_get_config_requires_secret_key_when_debug_disabled(monkeypatch):
    """``SECRET_KEY`` must be provided for non-debug deployments."""

    monkeypatch.delenv("SECRET_KEY", raising=False)
    monkeypatch.setenv("DEBUG", "0")

    config_module = load_config_module("config_missing_secret")

    with pytest.raises(RuntimeError, match="SECRET_KEY environment variable must be set"):
        config_module.get_config()
