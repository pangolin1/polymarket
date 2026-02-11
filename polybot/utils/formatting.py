"""Rich table formatters for CLI output."""

from __future__ import annotations

from rich.table import Table

from polybot.models.market import Market, OrderBook
from polybot.models.order import OpenOrder, Position


def markets_table(markets: list[Market]) -> Table:
    """Build a Rich table for a list of markets."""
    table = Table(title="Markets", show_lines=True)
    table.add_column("Condition ID", style="cyan", max_width=20)
    table.add_column("Question", style="white")
    table.add_column("Active", style="green")
    table.add_column("End Date", style="yellow")
    for m in markets:
        table.add_row(
            m.condition_id[:16] + "...",
            m.question,
            str(m.active),
            m.end_date_iso or "N/A",
        )
    return table


def orderbook_table(ob: OrderBook) -> Table:
    """Build a Rich table for an order book."""
    table = Table(title=f"Order Book: {ob.token_id[:16]}...", show_lines=True)
    table.add_column("Bid Price", style="green", justify="right")
    table.add_column("Bid Size", style="green", justify="right")
    table.add_column("Ask Price", style="red", justify="right")
    table.add_column("Ask Size", style="red", justify="right")

    max_rows = max(len(ob.bids), len(ob.asks))
    for i in range(min(max_rows, 10)):
        bid_price = ob.bids[i].price if i < len(ob.bids) else ""
        bid_size = ob.bids[i].size if i < len(ob.bids) else ""
        ask_price = ob.asks[i].price if i < len(ob.asks) else ""
        ask_size = ob.asks[i].size if i < len(ob.asks) else ""
        table.add_row(bid_price, bid_size, ask_price, ask_size)
    return table


def positions_table(positions: list[Position]) -> Table:
    """Build a Rich table for positions."""
    table = Table(title="Positions", show_lines=True)
    table.add_column("Asset", style="cyan", max_width=20)
    table.add_column("Outcome", style="white")
    table.add_column("Size", style="green", justify="right")
    table.add_column("Avg Price", justify="right")
    table.add_column("Cur Price", justify="right")
    table.add_column("P&L", justify="right")
    for p in positions:
        pnl = p.realized_pnl + p.unrealized_pnl
        pnl_style = "green" if pnl >= 0 else "red"
        table.add_row(
            p.asset[:16] + "..." if len(p.asset) > 16 else p.asset,
            p.outcome,
            f"{p.size:.2f}",
            f"{p.avg_price:.4f}",
            f"{p.cur_price:.4f}",
            f"[{pnl_style}]{pnl:+.4f}[/{pnl_style}]",
        )
    return table


def open_orders_table(orders: list[OpenOrder]) -> Table:
    """Build a Rich table for open orders."""
    table = Table(title="Open Orders", show_lines=True)
    table.add_column("Order ID", style="cyan", max_width=20)
    table.add_column("Side", style="white")
    table.add_column("Price", justify="right")
    table.add_column("Size", justify="right")
    table.add_column("Matched", justify="right")
    for o in orders:
        side_style = "green" if o.side == "BUY" else "red"
        table.add_row(
            o.order_id[:16] + "..." if len(o.order_id) > 16 else o.order_id,
            f"[{side_style}]{o.side}[/{side_style}]",
            o.price,
            o.original_size,
            o.size_matched,
        )
    return table
