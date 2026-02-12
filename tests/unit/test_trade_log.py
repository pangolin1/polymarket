"""Unit tests for CSV trade logger."""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from polybot.models.order import OrderRequest, OrderResponse, OrderType, Side
from polybot.trading.trade_log import TRADE_LOG_COLUMNS, TradeLogger


@pytest.fixture()
def log_path(tmp_path: Path) -> Path:
    return tmp_path / "test_trades.csv"


@pytest.fixture()
def trade_logger(log_path: Path) -> TradeLogger:
    return TradeLogger(path=log_path)


def _make_request(
    side: Side = Side.BUY,
    price: float = 0.55,
    size: float = 10.0,
) -> OrderRequest:
    return OrderRequest(
        token_id="tok_abc123",
        side=side,
        price=price,
        size=size,
    )


def _make_response(
    order_id: str = "order_xyz",
    status: str = "matched",
    success: bool = True,
) -> OrderResponse:
    return OrderResponse(
        order_id=order_id,
        status=status,
        success=success,
    )


class TestTradeLogger:
    def test_creates_file_with_header(
        self, trade_logger: TradeLogger, log_path: Path
    ) -> None:
        trade_logger.log_trade(_make_request(), _make_response())
        assert log_path.exists()

        with open(log_path, newline="") as f:
            reader = csv.reader(f)
            header = next(reader)
        assert header == TRADE_LOG_COLUMNS

    def test_logs_single_trade(
        self, trade_logger: TradeLogger, log_path: Path
    ) -> None:
        req = _make_request(side=Side.BUY, price=0.45, size=20.0)
        resp = _make_response(order_id="ord1", status="matched", success=True)
        trade_logger.log_trade(req, resp)

        rows = trade_logger.read_all()
        assert len(rows) == 1
        row = rows[0]
        assert row["token_id"] == "tok_abc123"
        assert row["side"] == "BUY"
        assert row["price"] == "0.4500"
        assert row["size"] == "20.00"
        assert row["order_type"] == "LMT"
        assert row["order_id"] == "ord1"
        assert row["status"] == "matched"
        assert row["success"] == "True"
        assert row["timestamp"]  # non-empty ISO timestamp

    def test_appends_multiple_trades(
        self, trade_logger: TradeLogger
    ) -> None:
        trade_logger.log_trade(
            _make_request(side=Side.BUY, price=0.40, size=10.0),
            _make_response(order_id="ord1"),
        )
        trade_logger.log_trade(
            _make_request(side=Side.SELL, price=0.60, size=5.0),
            _make_response(order_id="ord2"),
        )

        rows = trade_logger.read_all()
        assert len(rows) == 2
        assert rows[0]["side"] == "BUY"
        assert rows[0]["order_id"] == "ord1"
        assert rows[1]["side"] == "SELL"
        assert rows[1]["order_id"] == "ord2"

    def test_header_written_once(
        self, trade_logger: TradeLogger, log_path: Path
    ) -> None:
        for i in range(3):
            trade_logger.log_trade(
                _make_request(),
                _make_response(order_id=f"ord{i}"),
            )

        with open(log_path, newline="") as f:
            lines = f.readlines()
        # 1 header + 3 data rows
        assert len(lines) == 4

    def test_read_all_empty_file(self, trade_logger: TradeLogger) -> None:
        rows = trade_logger.read_all()
        assert rows == []

    def test_creates_parent_directories(self, tmp_path: Path) -> None:
        deep_path = tmp_path / "a" / "b" / "trades.csv"
        tl = TradeLogger(path=deep_path)
        tl.log_trade(_make_request(), _make_response())
        assert deep_path.exists()

    def test_persists_across_logger_instances(
        self, log_path: Path
    ) -> None:
        tl1 = TradeLogger(path=log_path)
        tl1.log_trade(
            _make_request(side=Side.BUY),
            _make_response(order_id="ord1"),
        )

        tl2 = TradeLogger(path=log_path)
        tl2.log_trade(
            _make_request(side=Side.SELL),
            _make_response(order_id="ord2"),
        )

        rows = tl2.read_all()
        assert len(rows) == 2
        assert rows[0]["order_id"] == "ord1"
        assert rows[1]["order_id"] == "ord2"
