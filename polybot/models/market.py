"""Market and Event models for Polymarket data."""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator


class Token(BaseModel):
    """A single outcome token within a market."""

    token_id: str
    outcome: str
    price: float = 0.0
    winner: bool = False


class Market(BaseModel):
    """A Polymarket binary market (condition)."""

    condition_id: str = Field(alias="conditionId", default="")
    question: str = ""
    description: str = ""
    market_slug: str = Field(alias="slug", default="")
    end_date_iso: str = Field(alias="endDateIso", default="")
    active: bool = True
    closed: bool = False
    neg_risk: bool = Field(alias="negRisk", default=False)
    tokens: list[Token] = []
    minimum_order_size: float = Field(alias="orderMinSize", default=0.0)
    minimum_tick_size: float = Field(alias="orderPriceMinTickSize", default=0.01)
    accepting_orders: bool = Field(alias="acceptingOrders", default=False)

    model_config = {"populate_by_name": True}

    @field_validator("tokens", mode="before")
    @classmethod
    def parse_tokens_json(cls, v: Any) -> Any:
        if isinstance(v, str):
            return json.loads(v)
        return v

    @field_validator("minimum_order_size", mode="before")
    @classmethod
    def coerce_order_size(cls, v: Any) -> float:
        if v is None:
            return 0.0
        return float(v)

    @field_validator("minimum_tick_size", mode="before")
    @classmethod
    def coerce_tick_size(cls, v: Any) -> float:
        if v is None:
            return 0.01
        return float(v)

    @model_validator(mode="before")
    @classmethod
    def build_tokens_from_clob_ids(cls, data: Any) -> Any:
        """Build Token list from clobTokenIds + outcomes + outcomePrices."""
        if not isinstance(data, dict):
            return data
        # If tokens already populated, skip
        if data.get("tokens"):
            return data

        clob_ids_raw = data.get("clobTokenIds")
        outcomes_raw = data.get("outcomes")
        prices_raw = data.get("outcomePrices")

        if not clob_ids_raw or not outcomes_raw:
            return data

        clob_ids: list[str] = json.loads(clob_ids_raw) if isinstance(clob_ids_raw, str) else clob_ids_raw
        outcomes: list[str] = json.loads(outcomes_raw) if isinstance(outcomes_raw, str) else outcomes_raw
        prices: list[str] = []
        if prices_raw:
            prices = json.loads(prices_raw) if isinstance(prices_raw, str) else prices_raw

        tokens: list[dict[str, Any]] = []
        for i, (tid, outcome) in enumerate(zip(clob_ids, outcomes)):
            price = float(prices[i]) if i < len(prices) else 0.0
            tokens.append({
                "token_id": tid,
                "outcome": outcome,
                "price": price,
            })
        data["tokens"] = tokens
        return data


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
