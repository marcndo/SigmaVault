
import csv
import sys
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

SOURCE_ACCOUNT = "SigmaVault Test Cash"
DEV_TAG = "SIGMAVAULT-SYNTHETIC-DEV"


def convert_records(input_path: Path, output_path: Path) -> int:
    fieldnames = [
        "date",
        "amount",
        "description",
        "asset_account",
        "opposing_account",
        "category",
        "currency",
        "tags",
    ]

    output_rows = []
    seen_ids = set()

    with input_path.open("r", encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)

        required = {
            "id",
            "description",
            "category",
            "subcategory",
            "amount",
            "currency",
            "type",
            "due_date",
            "status",
            "source",
        }

        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(
                f"Missing required columns: {sorted(missing)}"
            )

        for line_number, row in enumerate(reader, start=2):
            record_id = row["id"].strip()

            if not record_id or record_id in seen_ids:
                raise ValueError(
                    f"Missing or duplicate record ID at line {line_number}"
                )

            seen_ids.add(record_id)

            if row["status"].strip() != "unverified":
                raise ValueError(
                    f"Unexpected status for {record_id}"
                )

            if row["source"].strip() != "forecast":
                raise ValueError(
                    f"Unexpected source for {record_id}"
                )

            if row["currency"].strip() != "XAF":
                raise ValueError(
                    f"Unexpected currency for {record_id}"
                )

            try:
                amount = Decimal(row["amount"].strip())
            except (InvalidOperation, AttributeError) as exc:
                raise ValueError(
                    f"Invalid amount for {record_id}"
                ) from exc

            if not amount.is_finite() or amount <= 0:
                raise ValueError(
                    f"Amount must be positive for {record_id}"
                )

            record_type = row["type"].strip().lower()

            if record_type == "expense":
                signed_amount = -amount
                opposing_account = (
                    f"DEV {row['subcategory'].strip()}"
                )

            elif record_type == "income":
                signed_amount = amount
                opposing_account = "DEV Revenue Source"

            else:
                raise ValueError(
                    f"Unknown transaction type for {record_id}"
                )

            simulated_date = date.fromisoformat(
                row["due_date"].strip()
            ).isoformat()

            output_rows.append({
                "date": simulated_date,
                "amount": str(signed_amount),
                "description": (
                    f"[SYNTHETIC DEV] [{record_id}] "
                    f"{row['description'].strip()}"
                ),
                "asset_account": SOURCE_ACCOUNT,
                "opposing_account": opposing_account,
                "category": row["category"].strip(),
                "currency": "XAF",
                "tags": DEV_TAG,
            })

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with output_path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as target:
        writer = csv.DictWriter(
            target,
            fieldnames=fieldnames,
        )
        writer.writeheader()
        writer.writerows(output_rows)

    return len(output_rows)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit(
            "Usage: python script/prepare_firefly_import.py "
            "<input.csv> <output.csv>"
        )

    count = convert_records(
        Path(sys.argv[1]),
        Path(sys.argv[2]),
    )

    print(
        f"Prepared {count} synthetic "
        "Firefly III import records"
    )
