"""CLOB API client wrapping py-clob-client for trading and orderbook access."""

from __future__ import annotations

from typing import Any

from py_clob_client.client import ClobClient
from py_clob_client.clob_types import (
    ApiCreds,
    AssetType,
    BalanceAllowanceParams,
    OpenOrderParams,
    OrderArgs,
    OrderType,
    PartialCreateOrderOptions,
)

from polybot.config import Settings, get_settings
from polybot.models.market import OrderBook, OrderBookEntry
from polybot.models.order import OpenOrder, OrderResponse, Side
from polybot.utils.errors import ClobAPIError
from polybot.utils.logging import get_logger

logger = get_logger("clients.clob")

# EOA wallet = signature_type 0
SIGNATURE_TYPE_EOA = 0


class ClobClientWrapper:
    """Wrapper around ``py-clob-client`` with typed returns."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._client: ClobClient | None = None
        self._creds: ApiCreds | None = None

    @property
    def client(self) -> ClobClient:
        """Lazy-initialised authenticated CLOB client."""
        if self._client is None:
            self._client = ClobClient(
                host=self._settings.clob_api_url,
                chain_id=self._settings.chain_id,
                key=self._settings.private_key,
                signature_type=SIGNATURE_TYPE_EOA,
            )
            # Derive L2 API creds
            self._creds = self._client.create_or_derive_api_creds()
            self._client.set_api_creds(self._creds)
            logger.info("CLOB client initialised (L2 auth)")
        return self._client

    # ------------------------------------------------------------------
    # Read methods (no auth needed, but use the authenticated client)
    # ------------------------------------------------------------------

    def get_orderbook(self, token_id: str) -> OrderBook:
        """Fetch the order book for a token."""
        try:
            ob = self.client.get_order_book(token_id)
        except Exception as exc:
            raise ClobAPIError(f"Failed to get order book: {exc}") from exc

        bids = [OrderBookEntry(price=b.price, size=b.size) for b in ob.bids]
        asks = [OrderBookEntry(price=a.price, size=a.size) for a in ob.asks]
        return OrderBook(token_id=token_id, bids=bids, asks=asks)

    def get_price(self, token_id: str, side: Side) -> float:
        """Get the current price for a token on a given side."""
        try:
            price_str = self.client.get_price(token_id, side.value)
        except Exception as exc:
            raise ClobAPIError(f"Failed to get price: {exc}") from exc
        return float(price_str)

    def get_midpoint(self, token_id: str) -> float:
        """Get the midpoint price for a token."""
        try:
            mid_str = self.client.get_midpoint(token_id)
        except Exception as exc:
            raise ClobAPIError(f"Failed to get midpoint: {exc}") from exc
        return float(mid_str)

    # ------------------------------------------------------------------
    # Balance / Allowance
    # ------------------------------------------------------------------

    def get_balance_allowance(self, token_id: str = "") -> dict[str, Any]:
        """Check balance and allowance for collateral or a conditional token."""
        asset_type = AssetType.CONDITIONAL if token_id else AssetType.COLLATERAL
        params = BalanceAllowanceParams(
            asset_type=asset_type,
            token_id=token_id,
            signature_type=SIGNATURE_TYPE_EOA,
        )
        try:
            result: Any = self.client.get_balance_allowance(params)
        except Exception as exc:
            raise ClobAPIError(f"Failed to get balance/allowance: {exc}") from exc
        if isinstance(result, dict):
            return result
        return {"balance": str(result)}

    def update_balance_allowance(self, token_id: str = "") -> None:
        """Set the allowance for the exchange to spend collateral/tokens."""
        asset_type = AssetType.CONDITIONAL if token_id else AssetType.COLLATERAL
        params = BalanceAllowanceParams(
            asset_type=asset_type,
            token_id=token_id,
            signature_type=SIGNATURE_TYPE_EOA,
        )
        try:
            self.client.update_balance_allowance(params)
        except Exception as exc:
            raise ClobAPIError(f"Failed to update allowance: {exc}") from exc
        logger.info("Updated allowance for asset_type=%s token=%s", asset_type, token_id or "COLLATERAL")

    # ------------------------------------------------------------------
    # Trading (write methods)
    # ------------------------------------------------------------------

    def place_limit_order(
        self,
        token_id: str,
        side: Side,
        price: float,
        size: float,
        tick_size: str = "0.01",
        neg_risk: bool | None = None,
    ) -> OrderResponse:
        """Place a limit order on the CLOB."""
        order_args = OrderArgs(
            token_id=token_id,
            price=price,
            size=size,
            side=side.value,
        )
        options = PartialCreateOrderOptions(
            tick_size=tick_size,
            neg_risk=neg_risk,
        )
        try:
            signed_order = self.client.create_order(order_args, options)
            result: Any = self.client.post_order(signed_order, OrderType.GTC)
        except Exception as exc:
            raise ClobAPIError(f"Failed to place limit order: {exc}") from exc

        logger.info(
            "Placed limit %s order: token=%s price=%.4f size=%.2f result=%s",
            side.value,
            token_id,
            price,
            size,
            result,
        )

        if isinstance(result, dict):
            return OrderResponse(
                order_id=result.get("orderID", ""),
                status=result.get("status", ""),
                success=result.get("success", False),
                transact_order_id=result.get("transactOrderID", ""),
            )
        return OrderResponse(success=True, status=str(result))

    def get_open_orders(
        self,
        market: str = "",
        asset_id: str = "",
    ) -> list[OpenOrder]:
        """Fetch open orders, optionally filtered by market or asset."""
        params = OpenOrderParams(market=market, asset_id=asset_id)
        try:
            result: Any = self.client.get_orders(params)
        except Exception as exc:
            raise ClobAPIError(f"Failed to get open orders: {exc}") from exc

        orders: list[OpenOrder] = []
        items = result if isinstance(result, list) else []
        for item in items:
            if isinstance(item, dict):
                orders.append(
                    OpenOrder(
                        order_id=item.get("id", ""),
                        token_id=item.get("asset_id", ""),
                        side=item.get("side", ""),
                        price=item.get("price", ""),
                        original_size=item.get("original_size", ""),
                        size_matched=item.get("size_matched", ""),
                        outcome=item.get("outcome", ""),
                        asset_id=item.get("asset_id", ""),
                    )
                )
        return orders

    def cancel_order(self, order_id: str) -> bool:
        """Cancel an open order."""
        try:
            result: Any = self.client.cancel(order_id)
        except Exception as exc:
            raise ClobAPIError(f"Failed to cancel order: {exc}") from exc
        logger.info("Cancelled order %s: %s", order_id, result)
        return True

    def cancel_all_orders(self) -> bool:
        """Cancel all open orders."""
        try:
            self.client.cancel_all()
        except Exception as exc:
            raise ClobAPIError(f"Failed to cancel all orders: {exc}") from exc
        logger.info("Cancelled all open orders")
        return True
