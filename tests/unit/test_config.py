"""Unit tests for config module."""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from polybot.config import Settings, get_settings, reset_settings
from polybot.constants import CLOB_API_URL, DEFAULT_RPC_URL, GAMMA_API_URL


class TestSettings:
    def test_loads_from_env(self) -> None:
        env = {
            "POLY_PRIVATE_KEY": "0xdeadbeef",
            "POLY_WALLET_ADDRESS": "0x1234567890abcdef",
            "POLY_RPC_URL": DEFAULT_RPC_URL,
        }
        with patch.dict(os.environ, env, clear=False):
            reset_settings()
            s = Settings()  # type: ignore[call-arg]
            assert s.private_key == "0xdeadbeef"
            assert s.wallet_address == "0x1234567890abcdef"
            assert s.rpc_url == DEFAULT_RPC_URL
            assert s.chain_id == 137

    def test_defaults(self) -> None:
        env = {
            "POLY_PRIVATE_KEY": "0xabc",
            "POLY_WALLET_ADDRESS": "0xdef",
        }
        with patch.dict(os.environ, env, clear=False):
            s = Settings()  # type: ignore[call-arg]
            assert s.gamma_api_url == GAMMA_API_URL
            assert s.clob_api_url == CLOB_API_URL
            assert s.max_order_size_usdc == 50.0

    def test_custom_overrides(self) -> None:
        env = {
            "POLY_PRIVATE_KEY": "0xabc",
            "POLY_WALLET_ADDRESS": "0xdef",
            "POLY_RPC_URL": "https://custom-rpc.example.com",
            "POLY_MAX_ORDER_SIZE_USDC": "100.0",
        }
        with patch.dict(os.environ, env, clear=False):
            s = Settings()  # type: ignore[call-arg]
            assert s.rpc_url == "https://custom-rpc.example.com"
            assert s.max_order_size_usdc == 100.0

    def test_get_settings_singleton(self) -> None:
        env = {
            "POLY_PRIVATE_KEY": "0xabc",
            "POLY_WALLET_ADDRESS": "0xdef",
        }
        with patch.dict(os.environ, env, clear=False):
            reset_settings()
            s1 = get_settings()
            s2 = get_settings()
            assert s1 is s2
