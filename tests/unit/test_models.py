"""Unit tests for data models."""

from __future__ import annotations

import json

import pytest

from polybot.models.market import Event, Market, OrderBook, OrderBookEntry, Token
from polybot.models.order import OpenOrder, OrderRequest, OrderResponse, OrderType, Position, Side, Trade


class TestToken:
    def test_basic(self) -> None:
        t = Token(token_id="abc123", outcome="Yes", price=0.55)
        assert t.token_id == "abc123"
        assert t.outcome == "Yes"
        assert t.price == 0.55


class TestMarket:
    def test_basic(self) -> None:
        m = Market(condition_id="cond1", question="Will it rain?")
        assert m.condition_id == "cond1"
        assert m.active is True
        assert m.tokens == []

    def test_from_gamma_api_response(self) -> None:
        """Test parsing a market from the actual Gamma API response shape."""
        data = {
            "conditionId": "0xabc123",
            "question": "Will it rain?",
            "slug": "will-it-rain",
            "endDateIso": "2026-12-31",
            "active": True,
            "closed": False,
            "negRisk": False,
            "orderMinSize": 5.0,
            "orderPriceMinTickSize": 0.01,
            "acceptingOrders": True,
            "clobTokenIds": '["tok1", "tok2"]',
            "outcomes": '["Yes", "No"]',
            "outcomePrices": '["0.6", "0.4"]',
        }
        m = Market.model_validate(data)
        assert m.condition_id == "0xabc123"
        assert m.market_slug == "will-it-rain"
        assert m.end_date_iso == "2026-12-31"
        assert len(m.tokens) == 2
        assert m.tokens[0].token_id == "tok1"
        assert m.tokens[0].outcome == "Yes"
        assert m.tokens[0].price == 0.6
        assert m.tokens[1].outcome == "No"
        assert m.minimum_order_size == 5.0
        assert m.minimum_tick_size == 0.01

    def test_tokens_from_json_string(self) -> None:
        tokens_json = json.dumps([
            {"token_id": "tok1", "outcome": "Yes", "price": 0.6},
            {"token_id": "tok2", "outcome": "No", "price": 0.4},
        ])
        m = Market(condition_id="c1", question="Q?", tokens=tokens_json)  # type: ignore[arg-type]
        assert len(m.tokens) == 2
        assert m.tokens[0].outcome == "Yes"
        assert m.tokens[1].outcome == "No"

    def test_tokens_from_list(self) -> None:
        m = Market(
            condition_id="c1",
            question="Q?",
            tokens=[
                Token(token_id="t1", outcome="Yes"),
                Token(token_id="t2", outcome="No"),
            ],
        )
        assert len(m.tokens) == 2

    def test_null_tick_and_order_size(self) -> None:
        """Gamma API sometimes returns null for these fields."""
        data = {
            "conditionId": "0xabc",
            "question": "Q?",
            "orderMinSize": None,
            "orderPriceMinTickSize": None,
        }
        m = Market.model_validate(data)
        assert m.minimum_order_size == 0.0
        assert m.minimum_tick_size == 0.01


class TestEvent:
    def test_basic(self) -> None:
        e = Event(id="evt1", title="Some Event")
        assert e.id == "evt1"
        assert e.markets == []

    def test_markets_from_json_string(self) -> None:
        markets_json = json.dumps([
            {"conditionId": "c1", "question": "Q1?"},
        ])
        e = Event(id="e1", title="E", markets=markets_json)  # type: ignore[arg-type]
        assert len(e.markets) == 1


class TestOrderBook:
    def test_best_bid_ask_midpoint(self) -> None:
        ob = OrderBook(
            token_id="tok1",
            bids=[
                OrderBookEntry(price="0.45", size="100"),
                OrderBookEntry(price="0.44", size="200"),
            ],
            asks=[
                OrderBookEntry(price="0.47", size="50"),
                OrderBookEntry(price="0.48", size="150"),
            ],
        )
        assert ob.best_bid == 0.45
        assert ob.best_ask == 0.47
        assert ob.midpoint == pytest.approx(0.46)

    def test_empty_book(self) -> None:
        ob = OrderBook(token_id="tok1")
        assert ob.best_bid is None
        assert ob.best_ask is None
        assert ob.midpoint is None


class TestOrderRequest:
    def test_basic(self) -> None:
        req = OrderRequest(
            token_id="tok1",
            side=Side.BUY,
            price=0.50,
            size=10.0,
        )
        assert req.order_type == OrderType.LIMIT
        assert req.side == Side.BUY


class TestPosition:
    def test_defaults(self) -> None:
        p = Position()
        assert p.size == 0.0
        assert p.outcome == ""


class TestTrade:
    def test_defaults(self) -> None:
        t = Trade()
        assert t.id == ""
