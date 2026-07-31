# Navigate related data

Models make common USAspending relationships available as properties or query
builders.

## Award relationships

```python
from usaspending import USASpendingClient

with USASpendingClient() as client:
    award = client.awards.find_by_award_id("80GSFC18C0008")

    print(award.recipient.name)
    print(award.recipient.location.formatted_address)
    print(award.awarding_agency.name)
    print(award.funding_agency.name)
    print(award.place_of_performance.state_code)

    recent_transactions = award.transactions.order_by("action_date", "desc").limit(5)
    for transaction in recent_transactions:
        print(transaction.action_date, transaction.transaction_amount)
```

Relationships may use data already embedded in the award response or may issue
another request. Access them while the client remains open.

## Avoid accidental N+1 requests

Reading a lazy property for every row can turn one search into many detail
requests:

```python
with USASpendingClient() as client:
    awards = client.awards.search().contracts().fiscal_year(2024).limit(100)

    for award in awards:
        print(award.recipient.location.formatted_address)
```

When processing many awards:

- prefer properties already projected by the search endpoint;
- keep result limits explicit;
- enable caching for repeated lookups;
- use bulk downloads when the task requires comprehensive record-level data.

## Detached models

After the client closes, already-loaded scalar values remain readable. Accessing
a relationship that still needs the API raises `DetachedInstanceError`.

Reattach the model when later network access is intentional:

```python
with USASpendingClient() as new_client:
    award.reattach(new_client, recursive=True)
    print(award.subawards.count())
```

`recursive=True` also rebinds related models already loaded from the award.
