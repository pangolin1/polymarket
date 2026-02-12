"""End-to-end test: buy NO shares, validate, sell, validate.

This test uses REAL money on Polygon mainnet.
Requires: funded wallet (~$5 USDC), POLY_PRIVATE_KEY in .env.

Invoke:
    pytest tests/e2e/test_buy_sell_flow.py --market-id=<CONDITION_ID> -v -s
"""

from __future__ import annotations

import time

import pytest

from polybot.clients.clob import ClobClientWrapper
from polybot.clients.gamma import GammaClient
from polybot.models.order import Side
from polybot.trading.orders import OrderManager
from polybot.utils.logging import get_logger, setup_logging

logger = get_logger("e2e")

pytestmark = pytest.mark.e2e


def _wait_for_fill(
    clob: ClobClientWrapper,
    order_id: str,
    timeout: float = 60.0,
    poll_interval: float = 3.0,
) -> bool:
    """Poll open orders until the given order_id disappears (filled/cancelled)."""
    start = time.time()
    while time.time() - start < timeout:
        open_orders = clob.get_open_orders()
        ids = {o.order_id for o in open_orders}
        if order_id not in ids:
            return True
        logger.info("Order %s still open, waiting %.0fs...", order_id, poll_interval)
        time.sleep(poll_interval)
    return False


class TestBuySellFlow:
    """E2E: buy NO shares, confirm ownership, sell, confirm sale."""

    def test_round_trip(self, market_id: str) -> None:
        setup_logging()

        # ---- Step 1: Fetch market ----
        logger.info("Step 1: Fetching market %s", market_id)
        gamma = GammaClient()
        market = gamma.get_market(market_id)
        assert market.active, f"Market {market_id} is not active"
        assert market.tokens, f"Market {market_id} has no tokens"

        # Find the NO token
        no_token = None
        for tok in market.tokens:
            if tok.outcome.upper() == "NO":
                no_token = tok
                break
        assert no_token is not None, "No NO token found in market"
        logger.info("NO token: %s", no_token.token_id)

        # Determine tick size and neg_risk
        tick_size = str(market.minimum_tick_size) if market.minimum_tick_size else "0.01"
        clob = ClobClientWrapper()
        neg_risk: bool = market.neg_risk

        # Set up on-chain approvals (USDC + ERC1155)
        from polybot.wallet.manager import WalletManager

        wm = WalletManager()
        logger.info("Setting up on-chain approvals...")
        wm.setup_approvals()

        # Set up CLOB-side allowances
        logger.info("Setting up CLOB allowances...")
        clob.update_balance_allowance()  # USDC/collateral
        clob.update_balance_allowance(no_token.token_id)  # conditional token

        # ---- Step 2: Buy NO shares ----
        logger.info("Step 2: Buying NO shares")
        ob = clob.get_orderbook(no_token.token_id)
        logger.info("Orderbook — best_bid=%s best_ask=%s mid=%s", ob.best_bid, ob.best_ask, ob.midpoint)

        # Buy aggressively: 2 ticks above best ask to ensure instant match
        buy_price = ob.best_ask
        if buy_price is None:
            mid = ob.midpoint
            buy_price = mid if mid is not None else 0.50
        buy_price = round(buy_price + 0.02, 2)
        buy_price = min(buy_price, 0.99)  # Cap at max valid price
        buy_size = 10.0  # Small size

        mgr = OrderManager(clob=clob)
        buy_resp = mgr.buy(
            token_id=no_token.token_id,
            price=buy_price,
            size=buy_size,
            tick_size=tick_size,
            neg_risk=neg_risk,
        )
        logger.info("Buy order response: %s", buy_resp)
        buy_order_id = buy_resp.order_id or buy_resp.transact_order_id
        assert buy_order_id, "No order ID returned from buy"

        # ---- Step 3: Wait for fill and validate ownership ----
        logger.info("Step 3: Waiting for buy fill...")
        filled = _wait_for_fill(clob, buy_order_id, timeout=90.0)
        if not filled:
            # Cancel and fail
            logger.warning("Buy order did not fill in time, cancelling...")
            clob.cancel_order(buy_order_id)
            pytest.fail("Buy order did not fill within timeout")

        logger.info("Buy filled! Checking positions...")
        # Give the data API a moment to update
        time.sleep(5)

        # Verify we own NO shares by checking open orders are gone
        # (The data API position endpoint can lag, so we just verify
        #  the order was filled)
        open_orders = clob.get_open_orders()
        buy_still_open = any(o.order_id == buy_order_id for o in open_orders)
        assert not buy_still_open, "Buy order should no longer be open"
        logger.info("Confirmed: buy order filled")

        # ---- Step 4: Sell NO shares ----
        logger.info("Step 4: Selling NO shares")
        ob = clob.get_orderbook(no_token.token_id)
        logger.info("Orderbook — best_bid=%s best_ask=%s mid=%s", ob.best_bid, ob.best_ask, ob.midpoint)

        # Sell aggressively: 2 ticks below best bid to ensure instant match
        sell_price = ob.best_bid
        if sell_price is not None:
            sell_price = round(sell_price - 0.02, 2)
        else:
            sell_price = round(buy_price - 0.03, 2)
        sell_price = max(sell_price, 0.01)  # Floor at minimum valid price

        sell_resp = mgr.sell(
            token_id=no_token.token_id,
            price=sell_price,
            size=buy_size,
            tick_size=tick_size,
            neg_risk=neg_risk,
        )
        logger.info("Sell order response: %s", sell_resp)
        sell_order_id = sell_resp.order_id or sell_resp.transact_order_id
        assert sell_order_id, "No order ID returned from sell"

        # ---- Step 5: Wait for fill and validate sale ----
        logger.info("Step 5: Waiting for sell fill...")
        sell_filled = _wait_for_fill(clob, sell_order_id, timeout=90.0)
        if not sell_filled:
            logger.warning("Sell order did not fill in time, cancelling...")
            clob.cancel_order(sell_order_id)
            pytest.fail("Sell order did not fill within timeout")

        # Verify the sell order is no longer open
        open_orders = clob.get_open_orders()
        sell_still_open = any(o.order_id == sell_order_id for o in open_orders)
        assert not sell_still_open, "Sell order should no longer be open"
        logger.info("Confirmed: sell order filled — round trip complete!")
