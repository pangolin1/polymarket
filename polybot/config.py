"""Application configuration loaded from environment variables."""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings

from polybot.constants import (
    CLOB_API_URL,
    DATA_API_URL,
    DEFAULT_MAX_ORDER_SIZE_USDC,
    DEFAULT_RPC_URL,
    GAMMA_API_URL,
    POLYGON_CHAIN_ID,
)


class Settings(BaseSettings):
    """Bot configuration, loaded from environment with ``POLY_`` prefix."""

    private_key: str = Field(description="Hex-encoded EOA private key")
    wallet_address: str = Field(description="EOA wallet address")

    rpc_url: str = Field(default=DEFAULT_RPC_URL, description="Polygon RPC URL")
    chain_id: int = Field(default=POLYGON_CHAIN_ID, description="Chain ID")

    gamma_api_url: str = Field(default=GAMMA_API_URL)
    clob_api_url: str = Field(default=CLOB_API_URL)
    data_api_url: str = Field(default=DATA_API_URL)

    max_order_size_usdc: float = Field(
        default=DEFAULT_MAX_ORDER_SIZE_USDC,
        description="Maximum order size in USDC",
    )

    model_config = {
        "env_prefix": "POLY_",
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }


_settings: Settings | None = None


def get_settings() -> Settings:
    """Return the cached singleton ``Settings`` instance."""
    global _settings  # noqa: PLW0603
    if _settings is None:
        _settings = Settings()  # type: ignore[call-arg]
    return _settings


def reset_settings() -> None:
    """Reset cached settings (useful for testing)."""
    global _settings  # noqa: PLW0603
    _settings = None
