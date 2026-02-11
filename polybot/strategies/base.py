"""Abstract strategy interface for automated trading."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from polybot.models.market import Market


class BaseStrategy(ABC):
    """Base class for trading strategies.

    Subclasses implement ``evaluate`` to analyse a market and ``execute``
    to act on the analysis.
    """

    @abstractmethod
    def evaluate(self, market: Market) -> dict[str, Any]:
        """Analyse a market and return a signal/recommendation dict."""
        ...

    @abstractmethod
    def execute(self, market: Market, signal: dict[str, Any]) -> None:
        """Execute trades based on a signal from ``evaluate``."""
        ...
