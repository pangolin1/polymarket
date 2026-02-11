"""Wallet management: balances, allowances, credential derivation."""

from __future__ import annotations

from typing import Any

from web3 import Web3

from polybot.config import Settings, get_settings
from polybot.constants import (
    CONDITIONAL_TOKENS_ADDRESS,
    CTF_EXCHANGE_ADDRESS,
    ERC1155_ABI,
    ERC20_ABI,
    NEG_RISK_CTF_EXCHANGE_ADDRESS,
    USDC_ADDRESS,
    USDC_DECIMALS,
)
from polybot.utils.errors import WalletError
from polybot.utils.logging import get_logger

logger = get_logger("wallet")


class WalletManager:
    """Manage wallet balances, allowances, and on-chain interactions."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._w3: Web3 | None = None

    @property
    def w3(self) -> Web3:
        """Lazy-initialised Web3 connection."""
        if self._w3 is None:
            self._w3 = Web3(Web3.HTTPProvider(self._settings.rpc_url))
            if not self._w3.is_connected():
                raise WalletError(f"Cannot connect to RPC: {self._settings.rpc_url}")
            logger.info("Connected to RPC: %s", self._settings.rpc_url)
        return self._w3

    @property
    def address(self) -> str:
        return self._settings.wallet_address

    def get_pol_balance(self) -> float:
        """Get native POL (MATIC) balance in human-readable units."""
        balance_wei: int = self.w3.eth.get_balance(
            Web3.to_checksum_address(self.address)
        )
        return float(Web3.from_wei(balance_wei, "ether"))

    def get_usdc_balance(self) -> float:
        """Get USDC balance in human-readable units."""
        contract: Any = self.w3.eth.contract(
            address=Web3.to_checksum_address(USDC_ADDRESS),
            abi=ERC20_ABI,
        )
        raw: int = int(contract.functions.balanceOf(
            Web3.to_checksum_address(self.address)
        ).call())
        result: float = raw / (10**USDC_DECIMALS)
        return result

    def get_usdc_allowance(self, spender: str) -> float:
        """Check USDC allowance for a spender."""
        contract: Any = self.w3.eth.contract(
            address=Web3.to_checksum_address(USDC_ADDRESS),
            abi=ERC20_ABI,
        )
        raw: int = int(contract.functions.allowance(
            Web3.to_checksum_address(self.address),
            Web3.to_checksum_address(spender),
        ).call())
        result: float = raw / (10**USDC_DECIMALS)
        return result

    def get_conditional_token_balance(self, token_id: str) -> float:
        """Get ERC1155 conditional token balance."""
        contract: Any = self.w3.eth.contract(
            address=Web3.to_checksum_address(CONDITIONAL_TOKENS_ADDRESS),
            abi=ERC1155_ABI,
        )
        raw: int = int(contract.functions.balanceOf(
            Web3.to_checksum_address(self.address),
            int(token_id),
        ).call())
        result: float = raw / (10**USDC_DECIMALS)
        return result

    def check_exchange_approvals(self) -> dict[str, bool]:
        """Check if the exchange contracts are approved for conditional tokens."""
        contract: Any = self.w3.eth.contract(
            address=Web3.to_checksum_address(CONDITIONAL_TOKENS_ADDRESS),
            abi=ERC1155_ABI,
        )
        owner = Web3.to_checksum_address(self.address)
        ctf_approved: bool = contract.functions.isApprovedForAll(
            owner, Web3.to_checksum_address(CTF_EXCHANGE_ADDRESS)
        ).call()
        neg_risk_approved: bool = contract.functions.isApprovedForAll(
            owner, Web3.to_checksum_address(NEG_RISK_CTF_EXCHANGE_ADDRESS)
        ).call()
        return {
            "ctf_exchange": ctf_approved,
            "neg_risk_ctf_exchange": neg_risk_approved,
        }

    def wallet_status(self) -> dict[str, Any]:
        """Return a summary of wallet state."""
        pol = self.get_pol_balance()
        usdc = self.get_usdc_balance()
        approvals = self.check_exchange_approvals()
        return {
            "address": self.address,
            "pol_balance": pol,
            "usdc_balance": usdc,
            "approvals": approvals,
        }
