# Search transactions

The library exposes two intentionally different transaction workflows.

## Search across every award

`client.transactions.search()` returns one row per matching transaction across
all awards:

```python
from usaspending import USASpendingClient

with USASpendingClient() as client:
    transactions = (
        client.transactions.search()
        .contracts()
        .grants()
        .agency("National Aeronautics and Space Administration")
        .keywords("Mars")
        .fiscal_year(2024)
        .order_by("transaction_amount", "desc")
        .limit(25)
    )

    for transaction in transactions:
        amount = transaction.transaction_amount or 0
        print(transaction.action_date, transaction.award_identifier, amount)
```

Global transaction search requires at least one award type. Unlike award
search, it can combine categories in one query, such as contracts and grants.

## List transactions for one award

`award.transactions` uses the award-scoped endpoint:

```python
from usaspending import USASpendingClient

with USASpendingClient() as client:
    award = client.awards.find_by_award_id("80GSFC18C0008")
    latest = award.transactions.order_by("action_date", "desc").first()

    print(latest.action_date, latest.transaction_description)
```

Both workflows return `Transaction`, but the upstream row shapes differ.
Award-scoped rows have a transaction ID; global search rows identify their
parent award and therefore expose `transaction.id` as `None`.

## Amount semantics

`transaction.transaction_amount` returns the first nonzero reported figure:

1. federal action obligation;
2. loan face value;
3. original loan subsidy cost.

Negative values represent deobligations and are preserved. If every reported
figure is zero, the property returns `Decimal("0.00")`; `None` means the row
contains none of the supported amount fields.

## Important limits

- The global endpoint exposes at most the first 50,000 matching rows.
- Searches beyond that window raise `APIError` instead of silently truncating.
- `program_activities()` works for iteration, but the companion count endpoint
  does not support it; `count()` and `len()` therefore raise `ValidationError`.

Narrow the filters, apply `.limit()`, or use a bulk download for larger data
requests.
