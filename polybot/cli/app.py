"""Typer CLI application root."""

from __future__ import annotations

import typer

from polybot.cli.commands.markets import app as markets_app
from polybot.cli.commands.positions import app as positions_app
from polybot.cli.commands.trading import app as trading_app
from polybot.cli.commands.wallet import app as wallet_app
from polybot.utils.logging import setup_logging

app = typer.Typer(
    name="polybot",
    help="Polymarket programmatic trading bot.",
    no_args_is_help=True,
)

app.add_typer(markets_app, name="markets", help="Market discovery and info")
app.add_typer(trading_app, name="trade", help="Order management")
app.add_typer(wallet_app, name="wallet", help="Wallet status and balances")
app.add_typer(positions_app, name="positions", help="Position tracking")


@app.callback()
def main(verbose: bool = typer.Option(False, "--verbose", "-v")) -> None:
    """Polymarket trading bot CLI."""
    import logging

    level = logging.DEBUG if verbose else logging.INFO
    setup_logging(level)
