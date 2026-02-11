"""Custom exception hierarchy for the Polymarket trading bot."""

from __future__ import annotations


class PolybotError(Exception):
    """Base exception for all polybot errors."""


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
class ConfigError(PolybotError):
    """Invalid or missing configuration."""


# ---------------------------------------------------------------------------
# API / Network
# ---------------------------------------------------------------------------
class APIError(PolybotError):
    """Error communicating with an external API."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class GammaAPIError(APIError):
    """Error from the Gamma (markets) API."""


class ClobAPIError(APIError):
    """Error from the CLOB (trading) API."""


class DataAPIError(APIError):
    """Error from the Data (positions/activity) API."""


# ---------------------------------------------------------------------------
# Trading
# ---------------------------------------------------------------------------
class TradingError(PolybotError):
    """Base class for trading-related errors."""


class OrderValidationError(TradingError):
    """Order failed validation (price out of range, size too large, etc.)."""


class InsufficientBalanceError(TradingError):
    """Wallet does not have enough balance for the requested operation."""


class OrderPlacementError(TradingError):
    """Order was rejected by the exchange."""


# ---------------------------------------------------------------------------
# Wallet
# ---------------------------------------------------------------------------
class WalletError(PolybotError):
    """Wallet-related error (credentials, approvals, etc.)."""
