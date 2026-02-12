"""Order validation, safety checks, and placement logic."""

from __future__ import annotations

from polybot.clients.clob import ClobClientWrapper
from polybot.config import Settings, get_settings
from polybot.constants import PRICE_MAX, PRICE_MIN
from polybot.models.order import OpenOrder, OrderRequest, OrderResponse, Side
from polybot.trading.trade_log import TradeLogger
from polybot.utils.errors import OrderPlacementError, OrderValidationError
from polybot.utils.logging import get_logger

logger = get_logger("trading.orders")


class OrderManager:
    """Business logic for order validation, safety checks, and placement."""

    def __init__(
        self,
        clob: ClobClientWrapper | None = None,
        settings: Settings | None = None,
        trade_logger: TradeLogger | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._clob = clob or ClobClientWrapper(self._settings)
        self._trade_logger = trade_logger or TradeLogger()

    @property
    def clob(self) -> ClobClientWrapper:
        return self._clob

    def validate_order(self, request: OrderRequest) -> None:
        """Validate an order request. Raises ``OrderValidationError`` on failure."""
        if not (PRICE_MIN <= request.price <= PRICE_MAX):
            raise OrderValidationError(
                f"Price {request.price} out of range [{PRICE_MIN}, {PRICE_MAX}]"
            )
        if request.size <= 0:
            raise OrderValidationError(f"Size must be positive, got {request.size}")

        max_size = self._settings.max_order_size_usdc
        order_cost = request.price * request.size
        if order_cost > max_size:
            raise OrderValidationError(
                f"Order cost ${order_cost:.2f} exceeds max ${max_size:.2f}"
            )

    def place_order(
        self,
        request: OrderRequest,
        tick_size: str = "0.01",
        neg_risk: bool | None = None,
    ) -> OrderResponse:
        """Validate and place an order."""
        self.validate_order(request)

        logger.info(
            "Placing %s %s order: token=%s price=%.4f size=%.2f",
            request.order_type.value,
            request.side.value,
            request.token_id,
            request.price,
            request.size,
        )

        response = self._clob.place_limit_order(
            token_id=request.token_id,
            side=request.side,
            price=request.price,
            size=request.size,
            tick_size=tick_size,
            neg_risk=neg_risk,
        )

        if not response.success and response.status:
            raise OrderPlacementError(
                f"Order rejected: {response.status}"
            )

        self._trade_logger.log_trade(request, response)
        logger.info("Order placed: %s", response)
        return response

    def buy(
        self,
        token_id: str,
        price: float,
        size: float,
        tick_size: str = "0.01",
        neg_risk: bool | None = None,
    ) -> OrderResponse:
        """Place a buy limit order."""
        request = OrderRequest(
            token_id=token_id,
            side=Side.BUY,
            price=price,
            size=size,
        )
        return self.place_order(request, tick_size=tick_size, neg_risk=neg_risk)

    def sell(
        self,
        token_id: str,
        price: float,
        size: float,
        tick_size: str = "0.01",
        neg_risk: bool | None = None,
    ) -> OrderResponse:
        """Place a sell limit order."""
        request = OrderRequest(
            token_id=token_id,
            side=Side.SELL,
            price=price,
            size=size,
        )
        return self.place_order(request, tick_size=tick_size, neg_risk=neg_risk)

    def get_open_orders(
        self,
        market: str = "",
        asset_id: str = "",
    ) -> list[OpenOrder]:
        """Get open orders."""
        return self._clob.get_open_orders(market=market, asset_id=asset_id)

    def cancel_order(self, order_id: str) -> bool:
        """Cancel an open order."""
        return self._clob.cancel_order(order_id)

    def cancel_all_orders(self) -> bool:
        """Cancel all open orders."""
        return self._clob.cancel_all_orders()
