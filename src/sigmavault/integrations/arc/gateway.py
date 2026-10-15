from dataclasses import dataclass
from decimal import Decimal

from web3 import Web3


ARC_TESTNET_CHAIN_ID = 5042002
NATIVE_USDC_DECIMALS = 18


@dataclass(frozen=True)
class ArcTransactionReceipt:
    transaction_hash: str
    block_number: int
    status: int
    gas_used: int


class ArcGateway:
    """Read-only access to verified Arc Testnet state."""

    def __init__(self, rpc_url: str):
        if not isinstance(rpc_url, str) or not rpc_url.strip():
            raise ValueError("Arc RPC URL is required")

        self.web3 = Web3(
            Web3.HTTPProvider(
                rpc_url,
                request_kwargs={"timeout": 15},
            )
        )

    def verify_network(self) -> bool:
        """Reject disconnected or unexpected networks."""

        if not self.web3.is_connected():
            raise ConnectionError("Arc RPC is unreachable")

        actual_chain_id = self.web3.eth.chain_id

        if actual_chain_id != ARC_TESTNET_CHAIN_ID:
            raise ValueError(
                f"Unexpected chain ID: {actual_chain_id}"
            )

        return True

    def get_native_balance(self, address: str) -> Decimal:
        """Return native Arc USDC balance in human-readable units."""

        self.verify_network()

        if not Web3.is_address(address):
            raise ValueError("Invalid wallet address")

        balance_wei = self.web3.eth.get_balance(
            Web3.to_checksum_address(address)
        )

        return Decimal(balance_wei) / Decimal(
            10**NATIVE_USDC_DECIMALS
        )

    def get_transaction_receipt(
        self,
        transaction_hash: str,
    ) -> ArcTransactionReceipt:
        """Read a receipt without asserting payment settlement."""

        self.verify_network()

        if (
            not isinstance(transaction_hash, str)
            or not Web3.is_hex(transaction_hash)
            or len(transaction_hash) != 66
        ):
            raise ValueError("Invalid transaction hash")

        receipt = self.web3.eth.get_transaction_receipt(
            transaction_hash
        )

        return ArcTransactionReceipt(
            transaction_hash=receipt["transactionHash"].to_0x_hex(),
            block_number=receipt["blockNumber"],
            status=receipt["status"],
            gas_used=receipt["gasUsed"],
        )