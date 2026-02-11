#!/usr/bin/env python3
"""Generate an EOA keypair and write credentials to .env."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def main() -> None:
    from eth_account import Account

    env_path = Path(__file__).resolve().parent.parent / ".env"

    if env_path.exists():
        print(f"WARNING: {env_path} already exists.")
        resp = input("Overwrite wallet credentials? [y/N] ").strip().lower()
        if resp != "y":
            print("Aborted.")
            sys.exit(0)

    account = Account.create()  # type: ignore[no-untyped-call]
    private_key: str = account.key.hex()
    address: str = account.address

    # Read existing .env lines (if any) to preserve non-wallet entries
    existing_lines: list[str] = []
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                stripped = line.strip()
                if stripped.startswith("POLY_PRIVATE_KEY=") or stripped.startswith(
                    "POLY_WALLET_ADDRESS="
                ):
                    continue
                existing_lines.append(line.rstrip("\n"))

    with open(env_path, "w") as f:
        for line in existing_lines:
            f.write(line + "\n")
        if existing_lines and existing_lines[-1] != "":
            f.write("\n")
        f.write(f"POLY_PRIVATE_KEY={private_key}\n")
        f.write(f"POLY_WALLET_ADDRESS={address}\n")

    os.chmod(env_path, 0o600)

    print("Wallet generated successfully!")
    print(f"  Address: {address}")
    print(f"  Credentials written to: {env_path}")
    print()
    print("Next steps:")
    print(f"  1. Send ~$5 USDC (Polygon) to {address}")
    print(f"  2. Send a small amount of POL to {address} for gas")


if __name__ == "__main__":
    main()
