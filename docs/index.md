# USASpending ORM

USASpending ORM is a typed, ORM-style Python interface to the
[USAspending.gov API](https://api.usaspending.gov/). It turns API responses into
Python models and provides fluent query builders for awards, transactions,
recipients, agencies, spending summaries, Treasury Account Symbols, and bulk
downloads.

The design takes its cues from ActiveRecord and the Django ORM: results are
model objects with typed attributes and navigable associations, and queries are
built by chaining filter methods on a lazy, immutable builder that runs only
when you ask for results. If either is familiar, the shape here should be too,
with the federal API standing in for the database.

```python
from usaspending import USASpendingClient

with USASpendingClient() as client:
    awards = (
        client.awards.search()
        .contracts()
        .agency("National Aeronautics and Space Administration")
        .recipient_search_text("Space Exploration Technologies")
        .fiscal_year(2024)
        .order_by("Award Amount", "desc")
        .limit(5)
    )

    for award in awards:
        print(award.award_identifier, award.recipient.name, award.total_obligation)
```

## Why use it?

- **Fluent searches:** express API filters through chainable Python methods.
- **Typed models:** work with `date` and `Decimal` values instead of raw strings.
- **Navigable relationships:** move from an award to its recipient, transactions,
  funding records, accounts, and subawards.
- **Operational safeguards:** built-in pagination, retries, rate limiting, optional
  caching, and explicit result limits.
- **Raw data retained:** every model exposes the source response through `.raw`.

No API key is required.

[Install the library](getting-started/installation.md){ .md-button .md-button--primary }
[Follow the quickstart](getting-started/quickstart.md){ .md-button }

## Where to go next

- Learn the [core concepts](getting-started/core-concepts.md) before building a
  larger integration.
- Use the task-focused [guides](guides/search-awards.md) for common workflows.
- Consult the generated [Python reference](reference/client.md) for signatures and
  return types.
- Check the [endpoint mapping](usaspending-api/endpoint-mapping.md) when you need
  to understand how a library operation relates to the upstream API.
