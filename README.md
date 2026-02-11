# Polybot — Polymarket Trading Bot

Programmatic trading bot for [Polymarket](https://polymarket.com) on Polygon mainnet.

## Setup

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements-dev.txt
```

## Wallet Generation

```bash
python scripts/generate_wallet.py
```

This generates a fresh EOA keypair and writes it to `.env`. Then:

1. Send ~$5 **USDC** (on Polygon) to the printed address
2. Send a small amount of **POL** for gas

## Configuration

Copy and fill in the template:

```bash
cp .env.example .env
```

Required variables:
- `POLY_PRIVATE_KEY` — hex-encoded private key
- `POLY_WALLET_ADDRESS` — wallet address

Optional:
- `POLY_RPC_URL` — custom RPC (default: `https://polygon-rpc.com`)
- `POLY_MAX_ORDER_SIZE_USDC` — safety limit (default: 50)

## Verify Connection

```bash
python scripts/check_connection.py
```

## CLI Usage

```bash
# Market discovery
python -m polybot markets list --limit 10
python -m polybot markets search "election"
python -m polybot markets detail <condition_id>
python -m polybot markets orderbook <token_id>

# Wallet
python -m polybot wallet status
python -m polybot wallet balance

# Trading
python -m polybot trade buy <token_id> 10.0 --price 0.45
python -m polybot trade sell <token_id> 5.0 --price 0.60
python -m polybot trade orders
python -m polybot trade cancel <order_id>

# Positions
python -m polybot positions list
python -m polybot positions history
```

## Testing

```bash
# Unit tests (offline, mocked)
pytest tests/unit/ -v

# Integration tests (live read-only APIs)
pytest tests/integration/ -v

# E2E test (real money — requires funded wallet)
pytest tests/e2e/test_buy_sell_flow.py --market-id=<CONDITION_ID> -v -s
```

## Type Checking

```bash
mypy polybot/ --strict
```
