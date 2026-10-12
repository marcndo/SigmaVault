import httpx


class FireflyClient:
    """Read-only client for the Firefly III REST API."""

    def __init__(
        self,
        http_client: httpx.Client,
        token: str,
    ) -> None:
        self._http_client = http_client
        self._token = token


    def get_account_transactions(
        self,
        account_id: int,
        ) -> list[dict]:
        """Retrieve all transaction groups for a Firefly III account."""
    
        transactions = []
        page = 1
    
        while True:
            response = self._http_client.get(
                f"/api/v1/accounts/{account_id}/transactions",
                headers={
                    "Authorization": f"Bearer {self._token}",
                    "Accept": "application/json",
                },
                params={
                    "page": page,
                    "limit": 100,
                },
            )
    
            response.raise_for_status()
    
            payload = response.json()
    
            try:
                total_pages = payload["meta"]["pagination"]["total_pages"]
            
                if (
                    isinstance(total_pages, bool)
                    or not isinstance(total_pages, int)
                    or total_pages < 1
                ):
                    raise ValueError("Invalid Firefly III pagination metadata")
            
            except (KeyError, TypeError) as exc:
                raise ValueError(
                    "Invalid Firefly III pagination metadata"
                ) from exc
            
            # Validate the transaction collection before accepting it.
            try:
                page_transactions = payload["data"]
            except (KeyError, TypeError) as exc:
                raise ValueError(
                    "Invalid Firefly III transaction data"
                ) from exc
            
            if not isinstance(page_transactions, list):
                raise ValueError(
                    "Invalid Firefly III transaction data"
                )
            
            transactions.extend(page_transactions)
    
            if page >= total_pages:
                break
    
            page += 1
    
        return transactions
    
    
    