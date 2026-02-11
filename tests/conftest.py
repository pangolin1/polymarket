"""Shared fixtures and pytest configuration."""

from __future__ import annotations

from typing import Any, Generator

import pytest

from polybot.config import reset_settings


def pytest_addoption(parser: Any) -> None:
    """Add custom CLI options for pytest."""
    parser.addoption(
        "--market-id",
        action="store",
        default="",
        help="Condition ID for e2e market tests",
    )


@pytest.fixture
def market_id(request: pytest.FixtureRequest) -> str:
    """Market condition_id from --market-id CLI flag."""
    val: str = request.config.getoption("--market-id")
    if not val:
        pytest.skip("--market-id not provided")
    return val


@pytest.fixture(autouse=True)
def _reset_settings() -> Generator[None, None, None]:
    """Reset the settings singleton between tests."""
    reset_settings()
    yield
    reset_settings()
