"""Wallet CLI commands."""

from __future__ import annotations

import typer
from rich.console import Console

from polybot.wallet.manager import WalletManager

app = typer.Typer(no_args_is_help=True)
console = Console()


@app.command("status")
def wallet_status() -> None:
    """Show wallet status and balances."""
    wm = WalletManager()
    status = wm.wallet_status()
    console.print(f"[bold]Wallet Status[/bold]")
    console.print(f"  Address:  {status['address']}")
    console.print(f"  POL:      {status['pol_balance']:.6f}")
    console.print(f"  USDC:     {status['usdc_balance']:.6f}")
    approvals = status["approvals"]
    console.print(f"  CTF Exchange approved:          {approvals['ctf_exchange']}")
    console.print(f"  Neg Risk CTF Exchange approved: {approvals['neg_risk_ctf_exchange']}")


@app.command("balance")
def wallet_balance() -> None:
    """Show wallet balances."""
    wm = WalletManager()
    console.print(f"  POL:  {wm.get_pol_balance():.6f}")
    console.print(f"  USDC: {wm.get_usdc_balance():.6f}")
