"""Smithery FastMCP server entrypoint."""

from __future__ import annotations

from typing import Optional

from mcp.server.fastmcp import Context, FastMCP
from pydantic import BaseModel, Field
from smithery.decorators import smithery

from src.routes.crypto import build_crypto_price_result, build_heatmap_result, ServiceResult


class SessionConfig(BaseModel):
    """Session-level configuration exposed to Smithery clients."""

    default_time_period: str = Field(
        "24 hour",
        description="Default liquidation heatmap window when none is provided.",
    )
    allow_simulated: Optional[bool] = Field(
        default=None,
        description=(
            "Override simulated fallback behaviour. "
            "`true` always attaches simulated payloads, `false` disables them, "
            "and `null` defers to environment configuration."
        ),
    )


@smithery.server(config_schema=SessionConfig)
def create_server() -> FastMCP:
    """Create and configure the FastMCP server used by Smithery deployments."""

    server = FastMCP(name="Crypto Heatmap MCP Server")

    @server.tool()
    def get_crypto_price(symbol: str, ctx: Context) -> dict:
        """Fetch the latest USD price for a cryptocurrency symbol."""

        result: ServiceResult = build_crypto_price_result(symbol)
        if result.status_code >= 400:
            message = result.payload.get('error') or f'Failed to fetch price for {symbol}'
            raise RuntimeError(message)
        return result.payload

    @server.tool()
    def capture_heatmap(
        symbol: str,
        ctx: Context,
        time_period: Optional[str] = None,
        allow_simulated: Optional[bool] = None,
    ) -> dict:
        """Capture a liquidation heatmap for the requested symbol."""

        session_config: SessionConfig = ctx.session_config or SessionConfig()
        effective_time_period = time_period or session_config.default_time_period
        effective_allow_simulated = (
            allow_simulated if allow_simulated is not None else session_config.allow_simulated
        )

        result = build_heatmap_result(
            symbol,
            effective_time_period,
            effective_allow_simulated,
        )

        if result.status_code >= 500:
            message = result.payload.get('error') or 'BrowserCat client error while capturing heatmap.'
            raise RuntimeError(message)

        if result.status_code >= 400:
            # Return the structured payload (which may include a simulated fallback)
            return result.payload

        return result.payload

    return server
