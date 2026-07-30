"""Live shakeout of the new global TransactionsSearch builder.

Searches National Aeronautics and Space Administration contract AND grant
transactions (mixed categories, which spending_by_award cannot do) in
FY 2025 - FY 2026 whose keyword index matches termination language, sorted
most-negative first so deobligations lead.
"""

import csv
from pathlib import Path

from usaspending import USASpendingClient

CSV_FIELDS = ("Award ID", "Action Date", "Amount", "Type", "Recipient", "Description")
CSV_PATH = Path(__file__).with_suffix(".csv")


def output_transactions(transactions, csv_path):
    header = (
        f"{'Award ID':<16} {'Action Date':<12} {'Amount':>16} "
        f"{'Type':<16} {'Recipient':<38} Description"
    )
    print(header)
    print("-" * len(header))

    with Path(csv_path).open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=CSV_FIELDS)
        writer.writeheader()

        for txn in transactions:
            row = {
                "Award ID": txn.award_identifier or "n/a",
                "Action Date": str(txn.action_date or "n/a"),
                "Amount": txn.transaction_amount if txn.transaction_amount is not None else "n/a",
                "Type": txn.type_description or "n/a",
                "Recipient": txn.recipient_name or "n/a",
                "Description": (txn.transaction_description or "n/a").replace("\n", " "),
            }
            writer.writerow(row)

            amount = row["Amount"]
            amount_str = f"{amount:,.2f}" if amount != "n/a" else amount
            print(
                f"{row['Award ID'][:16]:<16} "
                f"{row['Action Date']:<12} "
                f"{amount_str:>16} "
                f"{row['Type'][:16]:<16} "
                f"{row['Recipient'][:38]:<38} "
                f"{row['Description'][:90]}"
            )


def main():
    client = USASpendingClient()

    query = (
        client.transactions.search()
        .award_type_codes("A", "B", "C", "D", "02", "03", "04", "05")
        .agency("National Aeronautics and Space Administration")
        .time_period("2024-10-01", "2026-09-30")
        .keywords("for convenience", "stop work", "terminated")
        .order_by("transaction_amount", "asc")
        .limit(500)
    )

    total = query.count()
    print(f"Matching transactions (contracts + grants, FY25-FY26): {total}\n")
    output_transactions(query, CSV_PATH)
    print(f"\nCSV exported to {CSV_PATH}")

    # Also exercise the count endpoint's bucket arithmetic per category
    contracts_only = (
        client.transactions.search()
        .contracts()
        .agency("National Aeronautics and Space Administration")
        .time_period("2024-10-01", "2026-09-30")
        .keywords("for convenience", "stop work", "terminated")
    )
    grants_only = (
        client.transactions.search()
        .grants()
        .agency("National Aeronautics and Space Administration")
        .time_period("2024-10-01", "2026-09-30")
        .keywords("for convenience", "stop work", "terminated")
    )
    c, g = contracts_only.count(), grants_only.count()
    print(
        f"\nBucket check: contracts={c}  grants={g}  contracts+grants={c + g}  "
        f"mixed-query count={total}"
    )


if __name__ == "__main__":
    main()
