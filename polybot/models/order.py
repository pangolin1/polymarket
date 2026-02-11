"""Order, Position, and Trade models."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel


class Side(str, Enum):
    """Order side."""

    BUY = "BUY"
    SELL = "SELL"


class OrderType(str, Enum):
    """Order type."""

    LIMIT = "LMT"
    MARKET = "MKT"


class OrderRequest(BaseModel):
    """Parameters for placing an order."""

    token_id: str
    side: Side
    price: float
    size: float
    order_type: OrderType = OrderType.LIMIT


class OrderResponse(BaseModel):
    """Response from order placement."""

    order_id: str = ""
    status: str = ""
    success: bool = False
    transact_order_id: str = ""


class OpenOrder(BaseModel):
    """An open (unfilled) order."""

    order_id: str = ""
    token_id: str = ""
    side: str = ""
    price: str = ""
    original_size: str = ""
    size_matched: str = ""
    outcome: str = ""
    asset_id: str = ""


class Position(BaseModel):
    """A position (ownership of outcome tokens)."""

    asset: str = ""
    condition_id: str = ""
    size: float = 0.0
    avg_price: float = 0.0
    cur_price: float = 0.0
    realized_pnl: float = 0.0
    unrealized_pnl: float = 0.0
    outcome: str = ""


class Trade(BaseModel):
    """A historical trade."""

    id: str = ""
    token_id: str = ""
    side: str = ""
    price: str = ""
    size: str = ""
    timestamp: str = ""
    status: str = ""
