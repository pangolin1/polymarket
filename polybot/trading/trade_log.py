"""CSV trade logger — appends one row per executed trade."""

from __future__ import annotations

import csv
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import IO

from polybot.models.order import OrderRequest, OrderResponse
from polybot.utils.logging import get_logger

logger = get_logger("trading.trade_log")

TRADE_LOG_COLUMNS = [
    "timestamp",
    "token_id",
    "side",
    "price",
    "size",
    "order_type",
    "order_id",
    "status",
    "success",
]

DEFAULT_LOG_PATH = "trades.csv"


class TradeLogger:
    """Append-only CSV trade log."""

    def __init__(self, path: str | Path | None = None) -> None:
        self._path = Path(path) if path is not None else Path(DEFAULT_LOG_PATH)

    @property
    def path(self) -> Path:
        return self._path

    def _ensure_header(self, f: IO[str]) -> None:
        """Write the CSV header if the file is empty."""
        if f.tell() == 0:
            writer = csv.writer(f)
            writer.writerow(TRADE_LOG_COLUMNS)

    def log_trade(
        self,
        request: OrderRequest,
        response: OrderResponse,
    ) -> None:
        """Append a trade record to the CSV log."""
        row = [
            datetime.now(timezone.utc).isoformat(),
            request.token_id,
            request.side.value,
            f"{request.price:.4f}",
            f"{request.size:.2f}",
            request.order_type.value,
            response.order_id,
            response.status,
            str(response.success),
        ]

        self._path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._path, "a", newline="") as f:
            self._ensure_header(f)
            writer = csv.writer(f)
            writer.writerow(row)

        logger.info("Trade logged: %s %s %.2f @ %.4f → %s",
                     request.side.value, request.token_id[:12],
                     request.size, request.price, response.status)

    def read_all(self) -> list[dict[str, str]]:
        """Read all trade records. Returns empty list if log doesn't exist."""
        if not self._path.exists():
            return []
        with open(self._path, newline="") as f:
            reader = csv.DictReader(f)
            return list(reader)
