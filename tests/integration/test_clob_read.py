"""Integration tests for CLOB client read-only operations (live)."""

from __future__ import annotations

import pytest

from polybot.clients.clob import ClobClientWrapper
from polybot.clients.gamma import GammaClient
from polybot.models.order import Side


pytestmark = pytest.mark.integration


class TestClobReadLive:
    """Live read-only tests against the CLOB API.

    These tests discover a real token_id from the Gamma API, then
    query the CLOB for orderbook/price data.
    """

    @pytest.fixture
    def live_token_id(self) -> str:
        """Find a token_id from an active market."""
        gamma = GammaClient()
        markets = gamma.get_markets(limit=10)
        for m in markets:
            if m.tokens:
                return m.tokens[0].token_id
        pytest.skip("No active market with tokens found")
        return ""  # unreachable, keeps mypy happy

    def test_get_orderbook(self, live_token_id: str) -> None:
        clob = ClobClientWrapper.__new__(ClobClientWrapper)
        # Use unauthenticated L0 client for read-only
        from py_clob_client.client import ClobClient

        clob._client = ClobClient(host="https://clob.polymarket.com")
        clob._settings = None  # type: ignore[assignment]
        clob._creds = None

        ob = clob.get_orderbook(live_token_id)
        assert ob.token_id == live_token_id
        # Orderbook may be empty for illiquid markets, but shouldn't error
