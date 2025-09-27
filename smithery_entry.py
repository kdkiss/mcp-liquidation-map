"""Smithery entrypoint that makes the src layout importable."""
from __future__ import annotations

import importlib
import sys
from pathlib import Path
from typing import Any


def _ensure_src_on_path() -> None:
    project_root = Path(__file__).resolve().parent
    src_dir = project_root / "src"
    if src_dir.is_dir():
        src_path = str(src_dir)
        if src_path not in sys.path:
            sys.path.insert(0, src_path)


def create_server(*args: Any, **kwargs: Any) -> Any:
    """Proxy to the real server factory used by Smithery."""
    try:
        server_module = importlib.import_module("mcp_liquidation_map.server")
    except ModuleNotFoundError:
        _ensure_src_on_path()
        server_module = importlib.import_module("mcp_liquidation_map.server")
    return getattr(server_module, "create_server")(*args, **kwargs)
