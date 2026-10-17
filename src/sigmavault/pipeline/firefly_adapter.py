from datetime import date

from sigmavault.integrations.firefly.adapter import (
    parse_firefly_transaction,
)
from sigmavault.integrations.firefly.client import FireflyClient
from sigmavault.pipeline.models import (
    CanonicalFinancialRecord,
    SourceRecordIdentity,
)


class FireflySourceAdapter:
    """Normalize Firefly III account transactions for the shared pipeline."""

    def __init__(
        self,
        client: FireflyClient,
        account_id: int,
        namespace: str,
    ) -> None:
        if (
            isinstance(account_id, bool)
            or not isinstance(account_id, int)
            or account_id <= 0
        ):
            raise ValueError("account_id must be a positive integer")

        if not isinstance(namespace, str) or not namespace.strip():
            raise ValueError("Firefly namespace must be nonempty")

        self.client = client
        self.account_id = account_id
        self.namespace = namespace.strip()

    def fetch_records(self) -> list[CanonicalFinancialRecord]:
        groups = self.client.get_account_transactions(self.account_id)
        records = []

        for group in groups:
            transaction = parse_firefly_transaction(
                group,
                status="actual",
            )

            split = group["attributes"]["transactions"][0]

            description = split.get("description")
            category = split.get("category_name")
            raw_date = split.get("date")

            if not isinstance(description, str) or not description.strip():
                raise ValueError("Missing Firefly transaction description")

            if not isinstance(raw_date, str):
                raise ValueError("Missing Firefly transaction date")

            try:
                transaction_date = date.fromisoformat(raw_date[:10])
            except ValueError as exc:
                raise ValueError("Invalid Firefly transaction date") from exc

            records.append(
                CanonicalFinancialRecord(
                    identity=SourceRecordIdentity(
                        provider="firefly",
                        namespace=self.namespace,
                        record_id=transaction.transaction_id,
                    ),
                    description=description,
                    category=category if isinstance(category, str) and category.strip() else "Uncategorized",
                    subcategory="",
                    amount=transaction.amount,
                    currency=transaction.currency,
                    direction=transaction.direction,
                    transaction_date=transaction_date,
                    due_date=None,
                    status="unverified",
                    source="confirmed",
                )
            )

        return records