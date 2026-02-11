#!/usr/bin/env python3
"""Verify API connectivity and credentials."""

from __future__ import annotations

import sys


def main() -> None:
    from polybot.clients.gamma import GammaClient
    from polybot.config import get_settings
    from polybot.wallet.manager import WalletManager

    print("Checking connectivity...\n")

    # 1. Config
    try:
        settings = get_settings()
        print(f"[OK] Config loaded — wallet: {settings.wallet_address}")
    except Exception as e:
        print(f"[FAIL] Config: {e}")
        sys.exit(1)

    # 2. Gamma API
    try:
        gamma = GammaClient()
        markets = gamma.get_markets(limit=1)
        print(f"[OK] Gamma API — fetched {len(markets)} market(s)")
    except Exception as e:
        print(f"[FAIL] Gamma API: {e}")

    # 3. RPC / Wallet
    try:
        wm = WalletManager()
        status = wm.wallet_status()
        print(f"[OK] RPC connected — POL: {status['pol_balance']:.6f}, USDC: {status['usdc_balance']:.6f}")
    except Exception as e:
        print(f"[FAIL] RPC/Wallet: {e}")

    # 4. CLOB (L2 auth)
    try:
        from polybot.clients.clob import ClobClientWrapper

        clob = ClobClientWrapper()
        _ = clob.client  # triggers credential derivation
        print("[OK] CLOB API — L2 auth derived")
    except Exception as e:
        print(f"[FAIL] CLOB API: {e}")

    print("\nDone.")


if __name__ == "__main__":
    main()
