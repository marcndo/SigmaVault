from decimal import Decimal
from unittest.mock import Mock

import pytest

from sigmavault.integrations.arc.wallet_snapshot import (
    capture_arc_wallet_snapshot,
)


ADDRESS = "0x0000000000000000000000000000000000000001"


def test_capture_wallet_snapshot():
    gateway = Mock()
    gateway.verify_network.return_value = True
    gateway.web3.eth.block_number = 12345
    gateway.web3.eth.chain_id = 5042002
    gateway.web3.eth.get_balance.return_value = 5 * 10**18

    snapshot = capture_arc_wallet_snapshot(gateway, ADDRESS)

    assert snapshot.chain_id == 5042002
    assert snapshot.block_number == 12345
    assert snapshot.native_usdc_balance == Decimal("5")

    gateway.web3.eth.get_balance.assert_called_once_with(
        ADDRESS,
        block_identifier=12345,
    )


def test_capture_wallet_snapshot_rejects_invalid_address():
    gateway = Mock()
    gateway.verify_network.return_value = True

    with pytest.raises(ValueError, match="Invalid wallet address"):
        capture_arc_wallet_snapshot(gateway, "not-an-address")

    gateway.web3.eth.get_balance.assert_not_called()