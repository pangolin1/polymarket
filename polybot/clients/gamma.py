"""Gamma API client for market discovery (no auth required)."""

from __future__ import annotations

from typing import Any

import httpx

from polybot.config import get_settings
from polybot.models.market import Event, Market
from polybot.utils.errors import GammaAPIError
from polybot.utils.logging import get_logger

logger = get_logger("clients.gamma")


class GammaClient:
    """Read-only client for the Polymarket Gamma API."""

    def __init__(self, base_url: str | None = None) -> None:
        self.base_url = base_url or get_settings().gamma_api_url

    def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        url = f"{self.base_url}{path}"
        logger.debug("GET %s params=%s", url, params)
        resp = httpx.get(url, params=params, timeout=30.0)
        if resp.status_code != 200:
            raise GammaAPIError(
                f"Gamma API error: {resp.status_code} {resp.text}",
                status_code=resp.status_code,
            )
        return resp.json()

    def get_markets(
        self,
        limit: int = 20,
        offset: int = 0,
        active: bool = True,
        closed: bool = False,
    ) -> list[Market]:
        """Fetch a list of markets."""
        params: dict[str, Any] = {
            "limit": limit,
            "offset": offset,
            "active": str(active).lower(),
            "closed": str(closed).lower(),
        }
        data = self._get("/markets", params=params)
        if not isinstance(data, list):
            data = []
        return [Market.model_validate(m) for m in data]

    def get_market(self, condition_id: str) -> Market:
        """Fetch a single market by condition_id."""
        data = self._get(f"/markets/{condition_id}")
        return Market.model_validate(data)

    def search_markets(self, query: str, limit: int = 20) -> list[Market]:
        """Search markets by text query."""
        params: dict[str, Any] = {"_q": query, "limit": limit}
        data = self._get("/markets", params=params)
        if not isinstance(data, list):
            data = []
        return [Market.model_validate(m) for m in data]

    def get_events(self, limit: int = 20, offset: int = 0) -> list[Event]:
        """Fetch a list of events."""
        params: dict[str, Any] = {"limit": limit, "offset": offset}
        data = self._get("/events", params=params)
        if not isinstance(data, list):
            data = []
        return [Event.model_validate(e) for e in data]

    def get_event(self, event_id: str) -> Event:
        """Fetch a single event by ID."""
        data = self._get(f"/events/{event_id}")
        return Event.model_validate(data)
