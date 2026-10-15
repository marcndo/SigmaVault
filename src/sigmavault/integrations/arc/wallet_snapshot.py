from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal

from web3 import Web3

from sigmavault.integrations.arc.gateway import ArcGateway


@dataclass(frozen=True)
class ArcWalletSnapshot:
    address: str
    chain_id: int
    block_number: int
    native_usdc_balance: Decimal
    observed_at: datetime


def capture_arc_wallet_snapshot(
    gateway: ArcGateway,
    address: str,
) -> ArcWalletSnapshot:
    """Capture a read-only observation of an Arc wallet."""

    gateway.verify_network()

    if not Web3.is_address(address):
        raise ValueError("Invalid wallet address")

    checksum_address = Web3.to_checksum_address(address)

    # Pin the balance and block number to the same chain state.
    block_number = gateway.web3.eth.block_number
    balance_wei = gateway.web3.eth.get_balance(
        checksum_address,
        block_identifier=block_number,
    )

    balance = Decimal(balance_wei) / Decimal(10**18)

    return ArcWalletSnapshot(
        address=checksum_address,
        chain_id=gateway.web3.eth.chain_id,
        block_number=block_number,
        native_usdc_balance=balance,
        observed_at=datetime.now(timezone.utc),
    )