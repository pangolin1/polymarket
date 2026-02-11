"""Market discovery CLI commands."""

from __future__ import annotations

import typer
from rich.console import Console

from polybot.clients.clob import ClobClientWrapper
from polybot.clients.gamma import GammaClient
from polybot.utils.formatting import markets_table, orderbook_table

app = typer.Typer(no_args_is_help=True)
console = Console()


@app.command("list")
def list_markets(
    limit: int = typer.Option(10, "--limit", "-l", help="Number of markets"),
    offset: int = typer.Option(0, "--offset", "-o", help="Offset for pagination"),
) -> None:
    """List active markets."""
    gamma = GammaClient()
    markets = gamma.get_markets(limit=limit, offset=offset)
    console.print(markets_table(markets))


@app.command("search")
def search_markets(
    query: str = typer.Argument(..., help="Search query"),
    limit: int = typer.Option(10, "--limit", "-l"),
) -> None:
    """Search markets by text."""
    gamma = GammaClient()
    markets = gamma.search_markets(query=query, limit=limit)
    if not markets:
        console.print("[yellow]No markets found.[/yellow]")
        return
    console.print(markets_table(markets))


@app.command("detail")
def market_detail(
    condition_id: str = typer.Argument(..., help="Market condition ID"),
) -> None:
    """Show detailed info for a market."""
    gamma = GammaClient()
    market = gamma.get_market(condition_id)
    console.print(f"[bold]{market.question}[/bold]")
    console.print(f"  Condition ID: {market.condition_id}")
    console.print(f"  Active: {market.active}")
    console.print(f"  Closed: {market.closed}")
    console.print(f"  End date: {market.end_date_iso or 'N/A'}")
    console.print(f"  Min order size: {market.minimum_order_size}")
    console.print(f"  Tick size: {market.minimum_tick_size}")
    if market.tokens:
        console.print("  Tokens:")
        for t in market.tokens:
            console.print(f"    {t.outcome}: {t.token_id[:20]}... price={t.price:.4f}")


@app.command("orderbook")
def show_orderbook(
    token_id: str = typer.Argument(..., help="Token ID"),
) -> None:
    """Show the order book for a token."""
    clob = ClobClientWrapper()
    ob = clob.get_orderbook(token_id)
    console.print(orderbook_table(ob))
    if ob.best_bid is not None:
        console.print(f"  Best bid: {ob.best_bid:.4f}")
    if ob.best_ask is not None:
        console.print(f"  Best ask: {ob.best_ask:.4f}")
    if ob.midpoint is not None:
        console.print(f"  Midpoint: {ob.midpoint:.4f}")
