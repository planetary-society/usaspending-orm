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
| `client.references`   | Current DEF code, country, and state reference data |
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

## Reference data

`client.references.def_codes()`, `.countries()`, and `.states()` each return a
fresh lazy query. The first evaluation fetches the reference list; subsequent
reads and filters on that evaluated query reuse the fetched rows. Use `.code()`
or `.codes()` to match codes, `.description()` to search names or descriptions
case-insensitively, and `.all()` when you need a plain list.

```python
with USASpendingClient() as client:
    countries = client.references.countries()
    for country in countries.codes("USA", "CAN"):
        print(country.code, country.name)

    states = client.references.states().description("alaska").all()
    for state in states:
        print(state.code, state.fips, state.name)
```

Country codes follow the API's reference data, including special location codes
such as `AX2`. State FIPS values remain strings, preserving leading zeros such
as Alaska's `"02"`; the state list also includes the District of Columbia and
territories.

## Models

Results are model objects such as `Award`, `Transaction`, `Recipient`, and
`Agency`. Models provide:

- normalized snake-case properties;
- parsed dates and decimal amounts;
- `.raw` access to the original response;
- related objects or query builders where the upstream data supports them.

Optional fields return `None` when the API does not report a value. A real
zero-dollar amount remains `Decimal("0.00")`.

Reference records (`DefCode`, `Country`, and `State`) are simple dataclasses
containing the server's reference fields, without lazy relationships or `.raw`.

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
