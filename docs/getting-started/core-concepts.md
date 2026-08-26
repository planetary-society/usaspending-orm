# Core concepts

## Client

`USASpendingClient` owns the HTTP session, retry behavior, rate limiter, and
resource entry points. Prefer a `with` block so the session closes reliably.

```python
from usaspending import USASpendingClient

with USASpendingClient() as client:
    award = client.awards.find_by_award_id("80GSFC18C0008")
```

## Resources

Client properties group related upstream operations:

| Resource              | Typical purpose                                    |
| --------------------- | -------------------------------------------------- |
| `client.awards`       | Find and search prime awards                       |
| `client.transactions` | Search transactions globally or for one award      |
| `client.subawards`    | Search subawards                                   |
| `client.recipients`   | Find and search recipient organizations            |
| `client.agencies`     | Agency summaries, subagencies, and office searches |
| `client.references`   | Current API reference data, including DEF codes    |
| `client.spending`     | Aggregated spending by recipient or geography      |
| `client.tas`          | Treasury Account Symbol hierarchy                  |
| `client.downloads`    | Queue server-side bulk exports                     |

## Query builders

Calling `.search()` returns a fluent builder. Filter methods clone it and return
a new query, so a shared base query can safely feed consumers that need
different filters.

```python
query = (
    client.awards.search()
    .contracts()
    .agency("National Aeronautics and Space Administration")
    .fiscal_year(2024)
    .limit(25)
)
```

Query builders handle pagination and expose a list-like interface, but they are
not in-memory lists. Some operations make separate API requests; see
[Query execution](../explanation/query-execution.md).

## Models

Results are model objects such as `Award`, `Transaction`, `Recipient`, and
`Agency`. Models provide:

- normalized snake-case properties;
- parsed dates and decimal amounts;
- `.raw` access to the original response;
- related objects or query builders where the upstream data supports them.

Optional fields return `None` when the API does not report a value. A real
zero-dollar amount remains `Decimal("0.00")`.

## Lazy loading and sessions

Some relationships require another API request. Access them while the creating
client is open. A model can be reattached to a new client when later lazy loads
are required:

```python
with USASpendingClient() as client:
    award = client.awards.find_by_award_id("80GSFC18C0008")

with USASpendingClient() as new_client:
    award.reattach(new_client, recursive=True)
    print(award.transactions.count())
```
