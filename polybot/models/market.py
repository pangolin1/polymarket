"""Market and Event models for Polymarket data."""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, field_validator


class Token(BaseModel):
    """A single outcome token within a market."""

    token_id: str
    outcome: str
    price: float = 0.0
    winner: bool = False


class Market(BaseModel):
    """A Polymarket binary market (condition)."""

    condition_id: str
    question: str
    description: str = ""
    market_slug: str = ""
    end_date_iso: str = ""
    active: bool = True
    closed: bool = False
    tokens: list[Token] = []
    minimum_order_size: float = 0.0
    minimum_tick_size: float = 0.01

    # Gamma API returns some fields as JSON strings
    @field_validator("tokens", mode="before")
    @classmethod
    def parse_tokens_json(cls, v: Any) -> Any:
        if isinstance(v, str):
            return json.loads(v)
        return v


class Event(BaseModel):
    """A Polymarket event (can contain multiple markets)."""

    id: str
    slug: str = ""
    title: str
    description: str = ""
    markets: list[Market] = []

    @field_validator("markets", mode="before")
    @classmethod
    def parse_markets_json(cls, v: Any) -> Any:
        if isinstance(v, str):
            return json.loads(v)
        return v


class OrderBookEntry(BaseModel):
    """A single entry in the order book (bid or ask)."""

    price: str
    size: str


class OrderBook(BaseModel):
    """Order book snapshot for a token."""

    token_id: str = ""
    bids: list[OrderBookEntry] = []
    asks: list[OrderBookEntry] = []

    @property
    def best_bid(self) -> float | None:
        if not self.bids:
            return None
        return max(float(b.price) for b in self.bids)

    @property
    def best_ask(self) -> float | None:
        if not self.asks:
            return None
        return min(float(a.price) for a in self.asks)

    @property
    def midpoint(self) -> float | None:
        bid = self.best_bid
        ask = self.best_ask
        if bid is None or ask is None:
            return None
        return (bid + ask) / 2.0
