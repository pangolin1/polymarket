"""Unit tests for order validation."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest

from polybot.config import Settings
from polybot.models.order import OrderRequest, OrderType, Side
from polybot.trading.orders import OrderManager
from polybot.utils.errors import OrderValidationError


def _make_settings(**overrides: object) -> Settings:
    defaults = {
        "POLY_PRIVATE_KEY": "0xdeadbeef",
        "POLY_WALLET_ADDRESS": "0x1234",
    }
    defaults.update(overrides)  # type: ignore[arg-type]
    with patch.dict(os.environ, defaults, clear=False):
        return Settings()  # type: ignore[call-arg]


class TestOrderValidation:
    def test_valid_order(self) -> None:
        settings = _make_settings()
        clob_mock = MagicMock()
        mgr = OrderManager(clob=clob_mock, settings=settings)

        req = OrderRequest(
            token_id="tok1", side=Side.BUY, price=0.50, size=10.0
        )
        mgr.validate_order(req)  # Should not raise

    def test_price_too_low(self) -> None:
        settings = _make_settings()
        clob_mock = MagicMock()
        mgr = OrderManager(clob=clob_mock, settings=settings)

        req = OrderRequest(
            token_id="tok1", side=Side.BUY, price=0.001, size=10.0
        )
        with pytest.raises(OrderValidationError, match="out of range"):
            mgr.validate_order(req)

    def test_price_too_high(self) -> None:
        settings = _make_settings()
        clob_mock = MagicMock()
        mgr = OrderManager(clob=clob_mock, settings=settings)

        req = OrderRequest(
            token_id="tok1", side=Side.BUY, price=1.0, size=10.0
        )
        with pytest.raises(OrderValidationError, match="out of range"):
            mgr.validate_order(req)

    def test_size_zero(self) -> None:
        settings = _make_settings()
        clob_mock = MagicMock()
        mgr = OrderManager(clob=clob_mock, settings=settings)

        req = OrderRequest(
            token_id="tok1", side=Side.BUY, price=0.50, size=0
        )
        with pytest.raises(OrderValidationError, match="positive"):
            mgr.validate_order(req)

    def test_exceeds_max_order_size(self) -> None:
        settings = _make_settings(POLY_MAX_ORDER_SIZE_USDC="10.0")
        clob_mock = MagicMock()
        mgr = OrderManager(clob=clob_mock, settings=settings)

        # 0.50 * 30 = $15, which exceeds $10 max
        req = OrderRequest(
            token_id="tok1", side=Side.BUY, price=0.50, size=30.0
        )
        with pytest.raises(OrderValidationError, match="exceeds max"):
            mgr.validate_order(req)

    def test_boundary_prices_valid(self) -> None:
        settings = _make_settings()
        clob_mock = MagicMock()
        mgr = OrderManager(clob=clob_mock, settings=settings)

        # Boundary: 0.01 and 0.99 should be valid
        for price in [0.01, 0.99]:
            req = OrderRequest(
                token_id="tok1", side=Side.BUY, price=price, size=1.0
            )
            mgr.validate_order(req)  # Should not raise
