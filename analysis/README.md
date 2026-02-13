# Polymarket Resolution Bias Analysis

## Purpose

Analyze historical Polymarket data to detect resolution bias in binary markets.
Specifically: do markets resolve "Yes" or "No" more often, and what would the P&L
be from blindly betting one side?

## Methodology

1. Fetch the 100 most recently closed binary markets with >$10k volume from the Gamma API
2. Filter to cleanly-resolved markets (one outcome price >= 0.99, other <= 0.01)
3. For each market, retrieve the Yes token price ~24 hours before resolution via the CLOB price history API
4. Compute P&L for two strategies: "Blind Yes" (always buy Yes) and "Blind No" (always buy No)
5. Aggregate win rates and P&L across all markets

## Limitations

- Sample is limited to 100 most recent markets per run (Gamma API pagination limit)
- Only markets with >$10k volume are included — low-volume markets are excluded
- Price 24h before close is approximate (nearest data point within a ~4h window)
- Markets with no price history fall back to `lastTradePrice` (which may differ from the 24h-before price)
- This is a retrospective analysis, not a trading strategy

## Run

```bash
venv/bin/python analysis/resolution_bias.py
```

---

## Results Log

### Run: 2026-02-13 10:19 UTC

| Strategy | Wins | Losses | Win Rate | Total P&L | Avg Buy Price |
|----------|------|--------|----------|-----------|---------------|
| Blind Yes | 55 | 45 | 55.0% | -44.81 | 0.555 |
| Blind No | 45 | 55 | 45.0% | -54.21 | 0.445 |

- Markets analyzed: 100
- Fallback prices used: 100
