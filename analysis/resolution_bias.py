"""
Resolution Bias Analysis for Polymarket

Fetches closed binary markets, checks whether "Yes" or "No" resolves more often,
and computes the P&L of blindly betting each side at the price ~24h before resolution.

Usage:
    venv/bin/python analysis/resolution_bias.py
"""

import json
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx
from rich.console import Console
from rich.table import Table

GAMMA_API = "https://gamma-api.polymarket.com"
CLOB_API = "https://clob.polymarket.com"
SCRIPT_DIR = Path(__file__).parent
README_PATH = SCRIPT_DIR / "README.md"

console = Console()


def fetch_closed_markets() -> list[dict]:
    """Fetch the 100 most recently closed markets with >$10k volume."""
    url = f"{GAMMA_API}/markets"
    params = {
        "closed": "true",
        "volume_num_min": 10000,
        "limit": 100,
        "order": "closedTime",
        "ascending": "false",
    }
    console.print("[bold]Fetching closed markets from Gamma API...[/bold]")
    resp = httpx.get(url, params=params, timeout=30)
    resp.raise_for_status()
    markets = resp.json()
    console.print(f"  Received {len(markets)} markets")
    return markets


def parse_json_field(value) -> list:
    """Parse a JSON string field, or return it if already a list."""
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        return json.loads(value)
    return []


def filter_binary_resolved(markets: list[dict]) -> list[dict]:
    """Keep only binary markets with a clear winner (one price >= 0.99, other <= 0.01)."""
    filtered = []
    for m in markets:
        outcomes = parse_json_field(m.get("outcomes", "[]"))
        prices = parse_json_field(m.get("outcomePrices", "[]"))

        if len(outcomes) != 2 or len(prices) != 2:
            continue

        try:
            p0, p1 = float(prices[0]), float(prices[1])
        except (ValueError, TypeError):
            continue

        has_winner = (p0 >= 0.99 and p1 <= 0.01) or (p1 >= 0.99 and p0 <= 0.01)
        if not has_winner:
            continue

        filtered.append(m)

    console.print(f"  {len(filtered)} binary, cleanly-resolved markets after filtering")
    return filtered


def get_price_24h_before(clob_token_id: str, closed_time_str: str) -> tuple[float | None, bool]:
    """
    Get the Yes token price ~24h before market resolution.

    Returns (price, used_fallback). If no price history, returns (None, False).
    """
    try:
        closed_dt = datetime.fromisoformat(closed_time_str.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None, False

    target_ts = int(closed_dt.timestamp()) - 86400  # 24h before close
    start_ts = target_ts - 7200  # 2h before target
    end_ts = target_ts + 7200  # 2h after target

    url = f"{CLOB_API}/prices-history"
    params = {
        "market": clob_token_id,
        "startTs": start_ts,
        "endTs": end_ts,
        "fidelity": 60,
    }

    try:
        resp = httpx.get(url, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        return None, False

    history = data.get("history", [])
    if not history:
        return None, False

    # Find price point closest to 24h before close
    best = None
    best_diff = float("inf")
    for point in history:
        ts = int(point.get("t", 0))
        diff = abs(ts - target_ts)
        if diff < best_diff:
            best_diff = diff
            best = point

    if best is None:
        return None, False

    try:
        price = float(best["p"])
    except (KeyError, ValueError, TypeError):
        return None, False

    return price, False


def analyze_markets(markets: list[dict]) -> list[dict]:
    """For each market, determine resolution and get 24h-before price."""
    results = []
    total = len(markets)

    console.print(f"\n[bold]Fetching price history for {total} markets...[/bold]")

    for i, m in enumerate(markets):
        question = m.get("question", "Unknown")
        short_q = question[:60] + "..." if len(question) > 60 else question
        console.print(f"  [{i+1}/{total}] {short_q}")

        outcomes = parse_json_field(m.get("outcomes", "[]"))
        prices = parse_json_field(m.get("outcomePrices", "[]"))
        clob_ids = parse_json_field(m.get("clobTokenIds", "[]"))
        closed_time = m.get("closedTime", "")

        p0, p1 = float(prices[0]), float(prices[1])

        # Determine which outcome index is "Yes"
        yes_idx = outcomes.index("Yes") if "Yes" in outcomes else 0
        yes_won = float(prices[yes_idx]) >= 0.99

        # Get the CLOB token ID for the Yes outcome
        if len(clob_ids) > yes_idx:
            yes_clob_id = clob_ids[yes_idx]
        else:
            continue

        # Try to get price 24h before close
        price_24h, _ = get_price_24h_before(yes_clob_id, closed_time)
        used_fallback = False

        if price_24h is None:
            # Fallback to lastTradePrice
            ltp = m.get("lastTradePrice")
            if ltp is not None:
                try:
                    price_24h = float(ltp)
                    used_fallback = True
                except (ValueError, TypeError):
                    pass

        if price_24h is None:
            continue

        # Skip degenerate prices
        if price_24h <= 0.0 or price_24h >= 1.0:
            continue

        results.append({
            "question": question,
            "yes_won": yes_won,
            "yes_price_24h": price_24h,
            "volume": m.get("volumeNum", 0),
            "closed_time": closed_time,
            "used_fallback": used_fallback,
        })

        # Rate limiting: 250ms between CLOB calls
        time.sleep(0.25)

    console.print(f"\n  {len(results)} markets with usable price data")
    return results


def compute_pnl(results: list[dict]) -> dict:
    """Compute P&L for Blind Yes and Blind No strategies."""
    yes_wins = 0
    yes_losses = 0
    yes_total_pnl = 0.0
    yes_prices = []

    no_wins = 0
    no_losses = 0
    no_total_pnl = 0.0
    no_prices = []

    for r in results:
        yes_price = r["yes_price_24h"]
        no_price = 1.0 - yes_price
        yes_won = r["yes_won"]

        # Blind Yes strategy
        yes_prices.append(yes_price)
        if yes_won:
            yes_wins += 1
            yes_total_pnl += (1.0 - yes_price) / yes_price
        else:
            yes_losses += 1
            yes_total_pnl -= 1.0

        # Blind No strategy
        no_prices.append(no_price)
        if not yes_won:
            no_wins += 1
            no_total_pnl += (1.0 - no_price) / no_price
        else:
            no_losses += 1
            no_total_pnl -= 1.0

    n = len(results)
    return {
        "total_markets": n,
        "yes": {
            "wins": yes_wins,
            "losses": yes_losses,
            "win_rate": yes_wins / n if n else 0,
            "total_pnl": yes_total_pnl,
            "avg_price": sum(yes_prices) / n if n else 0,
        },
        "no": {
            "wins": no_wins,
            "losses": no_losses,
            "win_rate": no_wins / n if n else 0,
            "total_pnl": no_total_pnl,
            "avg_price": sum(no_prices) / n if n else 0,
        },
    }


def print_summary(stats: dict) -> None:
    """Print a rich summary table."""
    table = Table(title="Resolution Bias Summary", show_lines=True)
    table.add_column("Strategy", style="bold")
    table.add_column("Wins", justify="right")
    table.add_column("Losses", justify="right")
    table.add_column("Win Rate", justify="right")
    table.add_column("Total P&L", justify="right")
    table.add_column("Avg Buy Price", justify="right")

    for name, key in [("Blind Yes", "yes"), ("Blind No", "no")]:
        s = stats[key]
        pnl_color = "green" if s["total_pnl"] >= 0 else "red"
        table.add_row(
            name,
            str(s["wins"]),
            str(s["losses"]),
            f"{s['win_rate']:.1%}",
            f"[{pnl_color}]{s['total_pnl']:+.2f}[/{pnl_color}]",
            f"{s['avg_price']:.3f}",
        )

    console.print()
    console.print(table)
    console.print(f"\nTotal markets analyzed: {stats['total_markets']}")


def print_detail_table(results: list[dict], max_rows: int = 30) -> None:
    """Print a per-market breakdown table (most recent first)."""
    table = Table(title=f"Per-Market Breakdown (top {max_rows} by recency)", show_lines=True)
    table.add_column("#", justify="right", style="dim")
    table.add_column("Question", max_width=50)
    table.add_column("Winner", justify="center")
    table.add_column("Yes Price 24h", justify="right")
    table.add_column("Yes P&L", justify="right")
    table.add_column("No P&L", justify="right")
    table.add_column("Fallback", justify="center")

    for i, r in enumerate(results[:max_rows]):
        yes_price = r["yes_price_24h"]
        no_price = 1.0 - yes_price
        winner = "Yes" if r["yes_won"] else "No"

        if r["yes_won"]:
            yes_pnl = (1.0 - yes_price) / yes_price
            no_pnl = -1.0
        else:
            yes_pnl = -1.0
            no_pnl = (1.0 - no_price) / no_price

        yes_color = "green" if yes_pnl >= 0 else "red"
        no_color = "green" if no_pnl >= 0 else "red"

        short_q = r["question"][:50] + "..." if len(r["question"]) > 50 else r["question"]

        table.add_row(
            str(i + 1),
            short_q,
            f"[bold]{winner}[/bold]",
            f"{yes_price:.3f}",
            f"[{yes_color}]{yes_pnl:+.2f}[/{yes_color}]",
            f"[{no_color}]{no_pnl:+.2f}[/{no_color}]",
            "*" if r["used_fallback"] else "",
        )

    console.print()
    console.print(table)
    fallback_count = sum(1 for r in results if r["used_fallback"])
    if fallback_count:
        console.print(f"\n[dim]* = used lastTradePrice fallback ({fallback_count} markets)[/dim]")


def append_results_to_readme(stats: dict, results: list[dict]) -> None:
    """Append a markdown summary entry to analysis/README.md."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    fallback_count = sum(1 for r in results if r["used_fallback"])

    entry = f"""
### Run: {now}

| Strategy | Wins | Losses | Win Rate | Total P&L | Avg Buy Price |
|----------|------|--------|----------|-----------|---------------|
| Blind Yes | {stats['yes']['wins']} | {stats['yes']['losses']} | {stats['yes']['win_rate']:.1%} | {stats['yes']['total_pnl']:+.2f} | {stats['yes']['avg_price']:.3f} |
| Blind No | {stats['no']['wins']} | {stats['no']['losses']} | {stats['no']['win_rate']:.1%} | {stats['no']['total_pnl']:+.2f} | {stats['no']['avg_price']:.3f} |

- Markets analyzed: {stats['total_markets']}
- Fallback prices used: {fallback_count}
"""

    with open(README_PATH, "a") as f:
        f.write(entry)

    console.print(f"\n[green]Results appended to {README_PATH}[/green]")


def main() -> None:
    console.print("[bold blue]Polymarket Resolution Bias Analysis[/bold blue]\n")

    markets = fetch_closed_markets()
    filtered = filter_binary_resolved(markets)
    results = analyze_markets(filtered)

    if not results:
        console.print("[red]No usable market data found. Exiting.[/red]")
        return

    stats = compute_pnl(results)
    print_summary(stats)
    print_detail_table(results)
    append_results_to_readme(stats, results)


if __name__ == "__main__":
    main()
