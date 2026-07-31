# Quickstart

## Find one award

Use the client as a context manager so related data can load while its HTTP
session is open:

```python
from usaspending import USASpendingClient

with USASpendingClient() as client:
    award = client.awards.find_by_award_id("80GSFC18C0008")

    print(award.award_identifier)
    print(award.recipient.name)
    print(award.period_of_performance.start_date)
    print(award.total_obligation)
```

Model properties normalize the API's field names and convert common values into
Python types. The unmodified source response remains available as `award.raw`.

## Search for awards

Searches are lazy: building the chain does not send a request. Iteration,
`.first()`, `.all()`, `.count()`, and `len(query)` execute it.

```python
from usaspending import USASpendingClient

with USASpendingClient() as client:
    query = (
        client.awards.search()
        .grants()
        .agency("National Aeronautics and Space Administration")
        .keywords("Mars")
        .fiscal_year(2024)
        .order_by("Award Amount", "desc")
        .limit(10)
    )

    print(f"{query.count()} matching grants")

    for award in query:
        amount = award.total_obligation or 0
        print(f"{award.award_identifier}: ${amount:,.2f}")
```

An award-type filter such as `.contracts()`, `.grants()`, or `.loans()` should
be set before executing a search.

## Handle missing results and errors

A lookup that matches nothing is not an error. `find_by_award_id()` and
`.first()` both return `None` when nothing matches, so check before using the
result:

```python
with USASpendingClient() as client:
    award = client.awards.find_by_award_id("not-an-award")

    if award is None:
        print("No matching award")
```

Failures raise instead. All library-specific exceptions inherit from
`USASpendingError`:

```python
from usaspending import USASpendingClient, USASpendingError

try:
    with USASpendingClient() as client:
        # An unsupported sort field is rejected before any request is sent.
        client.awards.search().contracts().order_by("Nonexistent Field").first()
except USASpendingError as error:
    print(f"USAspending request failed: {error}")
```

Continue with [Core concepts](core-concepts.md), then choose a guide for your
task.
