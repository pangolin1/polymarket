"""Position tracking CLI commands."""

from __future__ import annotations

import typer
from rich.console import Console
from rich.table import Table

from polybot.clients.data import DataClient
from polybot.utils.formatting import positions_table

app = typer.Typer(no_args_is_help=True)
console = Console()


@app.command("list")
def list_positions() -> None:
    """List current positions."""
    client = DataClient()
    positions = client.get_positions()
    if not positions:
        console.print("[yellow]No open positions.[/yellow]")
        return
    console.print(positions_table(positions))


@app.command("history")
def trade_history(
    limit: int = typer.Option(20, "--limit", "-l", help="Number of trades"),
) -> None:
    """Show trade history."""
    client = DataClient()
    trades = client.get_trades(limit=limit)
    if not trades:
        console.print("[yellow]No trade history.[/yellow]")
        return
    table = Table(title="Trade History", show_lines=True)
    table.add_column("ID", style="cyan", max_width=16)
    table.add_column("Side")
    table.add_column("Price", justify="right")
    table.add_column("Size", justify="right")
    table.add_column("Timestamp")
    table.add_column("Status")
    for t in trades:
        side_style = "green" if t.side == "BUY" else "red"
        table.add_row(
            t.id[:16] if t.id else "",
            f"[{side_style}]{t.side}[/{side_style}]",
            t.price,
            t.size,
            t.timestamp,
            t.status,
        )
    console.print(table)
