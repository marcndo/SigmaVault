from decimal import Decimal
from unittest.mock import Mock

import pytest

from sigmavault.integrations.arc.gateway import (
    ARC_TESTNET_CHAIN_ID,
    ArcGateway,
)


def make_gateway():
    gateway = ArcGateway("https://example.invalid")
    gateway.web3 = Mock()
    gateway.web3.is_connected.return_value = True
    gateway.web3.eth.chain_id = ARC_TESTNET_CHAIN_ID
    return gateway


def test_arc_gateway_verifies_expected_network():
    gateway = make_gateway()

    assert gateway.verify_network() is True


def test_arc_gateway_rejects_wrong_network():
    gateway = make_gateway()
    gateway.web3.eth.chain_id = 1

    with pytest.raises(ValueError, match="Unexpected chain ID"):
        gateway.verify_network()


def test_arc_gateway_rejects_disconnection():
    gateway = make_gateway()
    gateway.web3.is_connected.return_value = False

    with pytest.raises(ConnectionError):
        gateway.verify_network()


def test_arc_gateway_reads_native_balance():
    gateway = make_gateway()

    gateway.web3.eth.get_balance.return_value = (
        5 * 10**18
    )

    balance = gateway.get_native_balance(
        "0x0000000000000000000000000000000000000001"
    )

    assert balance == Decimal("5")