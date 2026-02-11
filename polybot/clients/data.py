"""Data API client for positions and trade history (no auth required)."""

from __future__ import annotations

from typing import Any

import httpx

from polybot.config import get_settings
from polybot.models.order import Position, Trade
from polybot.utils.errors import DataAPIError
from polybot.utils.logging import get_logger

logger = get_logger("clients.data")


class DataClient:
    """Read-only client for the Polymarket Data API."""

    def __init__(self, base_url: str | None = None) -> None:
        self.base_url = base_url or get_settings().data_api_url

    def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        url = f"{self.base_url}{path}"
        logger.debug("GET %s params=%s", url, params)
        resp = httpx.get(url, params=params, timeout=30.0)
        if resp.status_code != 200:
            raise DataAPIError(
                f"Data API error: {resp.status_code} {resp.text}",
                status_code=resp.status_code,
            )
        return resp.json()

    def get_positions(self, address: str | None = None) -> list[Position]:
        """Fetch positions for a wallet address."""
        addr = address or get_settings().wallet_address
        data = self._get(f"/positions", params={"user": addr})
        items: list[Any] = data if isinstance(data, list) else []
        positions: list[Position] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            cond_id: str = item.get("conditionId") or item.get("condition_id") or ""
            avg_p: float = float(item.get("avgPrice") or item.get("avg_price") or 0)
            cur_p: float = float(item.get("curPrice") or item.get("cur_price") or 0)
            r_pnl: float = float(item.get("realizedPnl") or item.get("realized_pnl") or 0)
            u_pnl: float = float(item.get("unrealizedPnl") or item.get("unrealized_pnl") or 0)
            positions.append(
                Position(
                    asset=item.get("asset", ""),
                    condition_id=cond_id,
                    size=float(item.get("size", 0)),
                    avg_price=avg_p,
                    cur_price=cur_p,
                    realized_pnl=r_pnl,
                    unrealized_pnl=u_pnl,
                    outcome=item.get("outcome", ""),
                )
            )
        return positions

    def get_trades(
        self, address: str | None = None, limit: int = 50
    ) -> list[Trade]:
        """Fetch trade history for a wallet address."""
        addr = address or get_settings().wallet_address
        data = self._get(f"/activity", params={"user": addr, "limit": limit})
        items: list[Any] = data if isinstance(data, list) else []
        trades: list[Trade] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            trades.append(
                Trade(
                    id=item.get("id", ""),
                    token_id=item.get("asset", ""),
                    side=item.get("side", ""),
                    price=item.get("price", ""),
                    size=item.get("size", ""),
                    timestamp=item.get("timestamp", ""),
                    status=item.get("status", ""),
                )
            )
        return trades
