"""Unit tests for Rich formatting helpers."""

from __future__ import annotations

from polybot.models.market import Market, OrderBook, OrderBookEntry
from polybot.models.order import OpenOrder, Position
from polybot.utils.formatting import (
    markets_table,
    open_orders_table,
    orderbook_table,
    positions_table,
)


class TestFormatting:
    def test_markets_table(self) -> None:
        markets = [
            Market(condition_id="a" * 30, question="Will X happen?"),
            Market(condition_id="b" * 30, question="Will Y happen?"),
        ]
        table = markets_table(markets)
        assert table.title == "Markets"
        assert table.row_count == 2

    def test_orderbook_table(self) -> None:
        ob = OrderBook(
            token_id="tok" * 10,
            bids=[OrderBookEntry(price="0.45", size="100")],
            asks=[OrderBookEntry(price="0.47", size="50")],
        )
        table = orderbook_table(ob)
        assert table.row_count == 1

    def test_positions_table(self) -> None:
        positions = [
            Position(
                asset="asset1",
                outcome="Yes",
                size=10.0,
                avg_price=0.45,
                cur_price=0.50,
                realized_pnl=0.0,
                unrealized_pnl=0.5,
            ),
        ]
        table = positions_table(positions)
        assert table.row_count == 1

    def test_open_orders_table(self) -> None:
        orders = [
            OpenOrder(
                order_id="order1",
                side="BUY",
                price="0.50",
                original_size="10",
                size_matched="0",
            ),
        ]
        table = open_orders_table(orders)
        assert table.row_count == 1

    def test_empty_tables(self) -> None:
        assert markets_table([]).row_count == 0
        assert positions_table([]).row_count == 0
        assert open_orders_table([]).row_count == 0
