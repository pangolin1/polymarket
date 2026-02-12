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
    NEG_RISK_ADAPTER_ADDRESS,
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
            # Polygon is a POA chain — inject the middleware
            from web3.middleware import geth_poa_middleware  # type: ignore[attr-defined]

            self._w3.middleware_onion.inject(geth_poa_middleware, layer=0)
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

    def _rpc_call_with_retry(self, fn: Any, *args: Any, retries: int = 3) -> Any:
        """Call an RPC function with retry on rate limit."""
        import time
        for attempt in range(retries):
            try:
                return fn(*args)
            except (ValueError, Exception) as exc:
                if "Too many requests" in str(exc) and attempt < retries - 1:
                    wait = 10 * (attempt + 1)
                    logger.warning("Rate limited, waiting %ds...", wait)
                    time.sleep(wait)
                else:
                    raise

    def _build_and_send_tx(self, tx: dict[str, Any]) -> str:
        """Sign and send a transaction, return the tx hash."""
        import time
        from eth_account import Account

        owner = Web3.to_checksum_address(self.address)
        tx["from"] = owner
        tx["chainId"] = self._settings.chain_id

        nonce: int = self._rpc_call_with_retry(
            self.w3.eth.get_transaction_count, owner
        )
        tx["nonce"] = nonce

        time.sleep(1)
        gas_price: int = self._rpc_call_with_retry(
            lambda: self.w3.eth.gas_price
        )
        tx["gasPrice"] = gas_price
        # Remove EIP-1559 fields that build_transaction may have added
        tx.pop("maxFeePerGas", None)
        tx.pop("maxPriorityFeePerGas", None)

        time.sleep(1)
        gas: int = self._rpc_call_with_retry(
            self.w3.eth.estimate_gas, tx
        )
        tx["gas"] = gas

        signed = Account.sign_transaction(tx, self._settings.private_key)
        tx_hash_raw: Any = self._rpc_call_with_retry(
            self.w3.eth.send_raw_transaction, signed.raw_transaction
        )
        tx_hash: str = tx_hash_raw.hex()
        logger.info("Tx sent: %s — waiting for confirmation...", tx_hash)

        # Poll for receipt with manual retry to handle rate limits
        receipt: Any = None
        for _ in range(30):
            time.sleep(5)
            try:
                receipt = self.w3.eth.get_transaction_receipt(tx_hash_raw)
                if receipt is not None:
                    break
            except Exception:
                continue

        if receipt is None:
            raise WalletError(f"Timed out waiting for tx: {tx_hash}")

        status: int = receipt.get("status", 0)
        if status != 1:
            raise WalletError(f"Transaction failed: {tx_hash}")
        logger.info("Transaction confirmed: %s", tx_hash)
        return tx_hash

    def approve_usdc(self, spender: str, amount: int | None = None) -> str:
        """Approve a spender to spend USDC (max uint256 by default)."""
        if amount is None:
            amount = 2**256 - 1  # max approval
        contract: Any = self.w3.eth.contract(
            address=Web3.to_checksum_address(USDC_ADDRESS),
            abi=ERC20_ABI,
        )
        data: bytes = contract.encodeABI(fn_name="approve", args=[
            Web3.to_checksum_address(spender),
            amount,
        ])
        tx: dict[str, Any] = {
            "to": Web3.to_checksum_address(USDC_ADDRESS),
            "data": data,
        }
        logger.info("Approving USDC for %s...", spender)
        return self._build_and_send_tx(tx)

    def approve_conditional_tokens(self, operator: str) -> str:
        """Set ERC1155 approval for all tokens to an operator."""
        contract: Any = self.w3.eth.contract(
            address=Web3.to_checksum_address(CONDITIONAL_TOKENS_ADDRESS),
            abi=ERC1155_ABI,
        )
        data: bytes = contract.encodeABI(fn_name="setApprovalForAll", args=[
            Web3.to_checksum_address(operator),
            True,
        ])
        tx: dict[str, Any] = {
            "to": Web3.to_checksum_address(CONDITIONAL_TOKENS_ADDRESS),
            "data": data,
        }
        logger.info("Approving conditional tokens for %s...", operator)
        return self._build_and_send_tx(tx)

    def setup_approvals(self) -> None:
        """Set up all required on-chain approvals for trading."""
        import time

        approvals = self.check_exchange_approvals()
        time.sleep(2)

        # USDC approvals for exchange contracts + neg risk adapter
        for label, addr in [
            ("CTF Exchange", CTF_EXCHANGE_ADDRESS),
            ("Neg Risk CTF Exchange", NEG_RISK_CTF_EXCHANGE_ADDRESS),
            ("Neg Risk Adapter", NEG_RISK_ADAPTER_ADDRESS),
        ]:
            allowance = self.get_usdc_allowance(addr)
            time.sleep(1)
            if allowance < 1_000:
                logger.info("Setting USDC approval for %s", label)
                self.approve_usdc(addr)
                time.sleep(3)

        # ERC1155 approvals for all three contracts
        ct_contract: Any = self.w3.eth.contract(
            address=Web3.to_checksum_address(CONDITIONAL_TOKENS_ADDRESS),
            abi=ERC1155_ABI,
        )
        owner = Web3.to_checksum_address(self.address)
        for label, addr in [
            ("CTF Exchange", CTF_EXCHANGE_ADDRESS),
            ("Neg Risk CTF Exchange", NEG_RISK_CTF_EXCHANGE_ADDRESS),
            ("Neg Risk Adapter", NEG_RISK_ADAPTER_ADDRESS),
        ]:
            approved: bool = ct_contract.functions.isApprovedForAll(
                owner, Web3.to_checksum_address(addr)
            ).call()
            if not approved:
                logger.info("Setting ERC1155 approval for %s", label)
                self.approve_conditional_tokens(addr)
                time.sleep(3)

        logger.info("All approvals set up")

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
