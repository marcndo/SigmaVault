import httpx
import pytest

from sigmavault.integrations.firefly.client import FireflyClient


def test_get_account_transactions_returns_transactions():
    """The client retrieves transactions for the requested account."""

    def mock_handler(request: httpx.Request) -> httpx.Response:
        # Verify that our client requests the correct endpoint.
        assert request.url.path == "/api/v1/accounts/17/transactions"

        # Verify that the authorization header is present.
        assert request.headers["Authorization"] == "Bearer test-token"

        # Simulate a successful Firefly III API response.
        return httpx.Response(
            status_code=200,
            json={
                "data": [
                    {
                        "id": "101",
                        "attributes": {
                            "transactions": [
                                {
                                    "type": "withdrawal",
                                    "amount": "25000",
                                    "currency_code": "XAF",
                                }
                            ]
                        },
                    }
                ],
                "meta": {
                    "pagination": {
                        "total_pages": 1,
                    }
                },
            },
        )

    transport = httpx.MockTransport(mock_handler)

    with httpx.Client(
        transport=transport,
        base_url="http://firefly.test",
    ) as http_client:

        firefly = FireflyClient(
            http_client=http_client,
            token="test-token",
        )

        transactions = firefly.get_account_transactions(account_id=17)

    assert len(transactions) == 1
    assert transactions[0]["id"] == "101"
    assert (
        transactions[0]["attributes"]["transactions"][0]["currency_code"]
        == "XAF"
    )
    
def test_get_account_transactions_retrieves_all_pages():
    """The client retrieves transactions from every API page."""

    requested_pages = []

    def mock_handler(request: httpx.Request) -> httpx.Response:
        # Extract the page number from the outgoing request.
        page = int(request.url.params["page"])

        requested_pages.append(page)

        # Simulate three pages returned by Firefly III.
        responses = {
            1: {
                "data": [{"id": "101"}],
                "meta": {"pagination": {"total_pages": 3}},
            },
            2: {
                "data": [{"id": "102"}],
                "meta": {"pagination": {"total_pages": 3}},
            },
            3: {
                "data": [{"id": "103"}],
                "meta": {"pagination": {"total_pages": 3}},
            },
        }

        return httpx.Response(
            status_code=200,
            json=responses[page],
        )

    transport = httpx.MockTransport(mock_handler)

    with httpx.Client(
        transport=transport,
        base_url="http://firefly.test",
    ) as http_client:

        firefly = FireflyClient(
            http_client=http_client,
            token="test-token",
        )

        transactions = firefly.get_account_transactions(account_id=17)

    assert requested_pages == [1, 2, 3]

    assert [transaction["id"] for transaction in transactions] == [
        "101",
        "102",
        "103",
    ]
    
    
def test_get_account_transactions_rejects_missing_pagination():
    """Reject responses without required pagination metadata."""

    def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            status_code=200,
            json={
                "data": [{"id": "101"}],
                # Pagination metadata is deliberately missing.
            },
        )

    transport = httpx.MockTransport(mock_handler)

    with httpx.Client(
        transport=transport,
        base_url="http://firefly.test",
    ) as http_client:

        firefly = FireflyClient(
            http_client=http_client,
            token="test-token",
        )

        with pytest.raises(
            ValueError,
            match="Invalid Firefly III pagination metadata",
        ):
            firefly.get_account_transactions(account_id=17)
            
def test_get_account_transactions_rejects_invalid_data():
    """Reject an API response whose data field is not a list."""

    def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            status_code=200,
            json={
                "data": {"id": "101"},
                "meta": {
                    "pagination": {
                        "total_pages": 1,
                    }
                },
            },
        )

    transport = httpx.MockTransport(mock_handler)

    with httpx.Client(
        transport=transport,
        base_url="http://firefly.test",
    ) as http_client:

        firefly = FireflyClient(
            http_client=http_client,
            token="test-token",
        )

        with pytest.raises(
            ValueError,
            match="Invalid Firefly III transaction data",
        ):
            firefly.get_account_transactions(account_id=17)
     
            
def test_get_account_transactions_raises_on_unauthorized():
    """Reject API requests when Firefly III denies authentication."""

    def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            status_code=401,
            json={
                "message": "Unauthenticated."
            },
        )

    transport = httpx.MockTransport(mock_handler)

    with httpx.Client(
        transport=transport,
        base_url="http://firefly.test",
    ) as http_client:

        firefly = FireflyClient(
            http_client=http_client,
            token="invalid-token",
        )

        with pytest.raises(httpx.HTTPStatusError) as exc_info:
            firefly.get_account_transactions(account_id=17)

    assert exc_info.value.response.status_code == 401
    
def test_get_account_transactions_raises_on_server_error():
    """Reject transaction retrieval when Firefly III returns HTTP 500."""

    def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            status_code=500,
            json={
                "message": "Internal Server Error"
            },
        )

    transport = httpx.MockTransport(mock_handler)

    with httpx.Client(
        transport=transport,
        base_url="http://firefly.test",
    ) as http_client:

        firefly = FireflyClient(
            http_client=http_client,
            token="test-token",
        )

        with pytest.raises(httpx.HTTPStatusError) as exc_info:
            firefly.get_account_transactions(account_id=17)

    assert exc_info.value.response.status_code == 500
    
    
def test_get_account_transactions_rejects_partial_results():
    """Never return incomplete transactions when a later page fails."""

    requested_pages = []

    def mock_handler(request: httpx.Request) -> httpx.Response:
        page = int(request.url.params["page"])
        requested_pages.append(page)

        if page == 1:
            return httpx.Response(
                status_code=200,
                json={
                    "data": [{"id": "101"}],
                    "meta": {
                        "pagination": {
                            "total_pages": 2,
                        }
                    },
                },
            )

        if page == 2:
            return httpx.Response(
                status_code=500,
                json={
                    "message": "Internal Server Error",
                },
            )

        raise AssertionError(f"Unexpected page requested: {page}")

    transport = httpx.MockTransport(mock_handler)

    with httpx.Client(
        transport=transport,
        base_url="http://firefly.test",
    ) as http_client:

        firefly = FireflyClient(
            http_client=http_client,
            token="test-token",
        )

        with pytest.raises(httpx.HTTPStatusError) as exc_info:
            firefly.get_account_transactions(account_id=17)

    assert requested_pages == [1, 2]
    assert exc_info.value.response.status_code == 500
    
    
def test_get_account_transactions_raises_on_connection_failure():
    """Propagate network connection failures."""

    def mock_handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError(
            "Unable to connect to Firefly III",
            request=request,
        )

    transport = httpx.MockTransport(mock_handler)

    with httpx.Client(
        transport=transport,
        base_url="http://firefly.test",
    ) as http_client:

        firefly = FireflyClient(
            http_client=http_client,
            token="test-token",
        )

        with pytest.raises(httpx.ConnectError):
            firefly.get_account_transactions(account_id=17)
  
            
def test_get_account_transactions_raises_on_timeout():
    """Propagate timeouts instead of returning incomplete data."""

    requested_pages = []

    def mock_handler(request: httpx.Request) -> httpx.Response:
        page = int(request.url.params["page"])
        requested_pages.append(page)

        if page == 1:
            return httpx.Response(
                status_code=200,
                json={
                    "data": [{"id": "101"}],
                    "meta": {
                        "pagination": {
                            "total_pages": 2,
                        }
                    },
                },
            )

        if page == 2:
            raise httpx.ReadTimeout(
                "Firefly III took too long to respond",
                request=request,
            )

        raise AssertionError(f"Unexpected page requested: {page}")

    transport = httpx.MockTransport(mock_handler)

    with httpx.Client(
        transport=transport,
        base_url="http://firefly.test",
        timeout=5.0,
    ) as http_client:

        firefly = FireflyClient(
            http_client=http_client,
            token="test-token",
        )

        with pytest.raises(httpx.ReadTimeout):
            firefly.get_account_transactions(account_id=17)

    assert requested_pages == [1, 2]