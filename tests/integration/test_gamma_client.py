"""Integration tests for the Gamma API client (live, read-only)."""

from __future__ import annotations

import pytest

from polybot.clients.gamma import GammaClient


pytestmark = pytest.mark.integration


class TestGammaClientLive:
    """Live read-only tests against the Gamma API."""

    def test_get_markets_returns_list(self) -> None:
        gamma = GammaClient()
        markets = gamma.get_markets(limit=5)
        assert isinstance(markets, list)
        assert len(markets) > 0
        # Each market should have a condition_id and question
        for m in markets:
            assert m.condition_id
            assert m.question

    def test_search_markets(self) -> None:
        gamma = GammaClient()
        markets = gamma.search_markets("election", limit=3)
        assert isinstance(markets, list)
        # Search may return 0 if no matching markets, that's OK

    def test_get_events(self) -> None:
        gamma = GammaClient()
        events = gamma.get_events(limit=3)
        assert isinstance(events, list)
