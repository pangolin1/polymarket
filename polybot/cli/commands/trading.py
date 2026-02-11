"""Trading CLI commands."""

from __future__ import annotations

import typer
from rich.console import Console

from polybot.trading.orders import OrderManager
from polybot.utils.formatting import open_orders_table

app = typer.Typer(no_args_is_help=True)
console = Console()


@app.command("buy")
def buy(
    token_id: str = typer.Argument(..., help="Token ID to buy"),
    size: float = typer.Argument(..., help="Number of shares"),
    price: float = typer.Option(..., "--price", "-p", help="Limit price (0.01-0.99)"),
) -> None:
    """Place a buy limit order."""
    mgr = OrderManager()
    resp = mgr.buy(token_id=token_id, price=price, size=size)
    console.print(f"[green]Order placed![/green] ID: {resp.order_id or resp.transact_order_id}")
    console.print(f"  Status: {resp.status}")


@app.command("sell")
def sell(
    token_id: str = typer.Argument(..., help="Token ID to sell"),
    size: float = typer.Argument(..., help="Number of shares"),
    price: float = typer.Option(..., "--price", "-p", help="Limit price (0.01-0.99)"),
) -> None:
    """Place a sell limit order."""
    mgr = OrderManager()
    resp = mgr.sell(token_id=token_id, price=price, size=size)
    console.print(f"[red]Sell order placed![/red] ID: {resp.order_id or resp.transact_order_id}")
    console.print(f"  Status: {resp.status}")


@app.command("orders")
def list_orders() -> None:
    """List open orders."""
    mgr = OrderManager()
    orders = mgr.get_open_orders()
    if not orders:
        console.print("[yellow]No open orders.[/yellow]")
        return
    console.print(open_orders_table(orders))


@app.command("cancel")
def cancel_order(
    order_id: str = typer.Argument(..., help="Order ID to cancel"),
) -> None:
    """Cancel an open order."""
    mgr = OrderManager()
    mgr.cancel_order(order_id)
    console.print(f"[green]Order {order_id} cancelled.[/green]")
