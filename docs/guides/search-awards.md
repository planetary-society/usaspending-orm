# Search awards

Award search returns one model per prime award. Start with
`client.awards.search()`, choose one award-type category, add filters, and only
then execute the query.

## Build a focused query

```python
from usaspending import USASpendingClient

with USASpendingClient() as client:
    query = (
        client.awards.search()
        .contracts()
        .agency("National Aeronautics and Space Administration")
        .recipient_search_text("California Institute of Technology")
        .time_period("2023-10-01", "2024-09-30")
        .order_by("Award Amount", "desc")
        .limit(20)
    )

    for award in query:
        print(award.award_identifier, award.description)
```

Use `.fiscal_year(2024)` instead of `.time_period(...)` when federal fiscal-year
boundaries are what you mean.

`.recipient_search_text(...)` matches the recipient's registered name, not a
colloquial one. Jet Propulsion Laboratory awards, for example, are reported
under California Institute of Technology.

## Awarding agency or funding agency

`.agency(name)` filters on the **awarding** top-tier agency by default, which
matches the agency view on USAspending.gov. The awarding agency administers the
award; the funding agency supplies the money, and the two differ whenever one
agency pays for work another agency contracts. Choosing the wrong side quietly
changes the totals rather than raising an error, so state which one your
analysis means:

```python
awarding = client.awards.search().contracts().agency(
    "National Aeronautics and Space Administration"
)
funding = client.awards.search().contracts().agency(
    "National Aeronautics and Space Administration", agency_type="funding"
)
```

Awarding-side totals include interagency reimbursable work: contracts another
agency funds but this agency administers. Funding-side totals include work this
agency pays for but another agency administers.

Pass `tier="subtier"` for a sub-agency or office. Use `.agencies(...)` with one
dictionary per agency to filter on several at once:

```python
query = client.awards.search().contracts().agencies(
    {"name": "National Aeronautics and Space Administration",
     "type": "awarding", "tier": "toptier"},
)
```

## Award-type filters

Convenience methods select the corresponding USAspending award-type codes:

- `.contracts()`
- `.grants()`
- `.loans()`
- `.direct_payments()`
- `.idvs()`
- `.other_assistance()`

Award search accepts only one category at a time because the upstream endpoint
offers different fields for different categories. Use
`.award_type_codes(...)` when exact subtypes matter.

## Count before fetching

```python
with USASpendingClient() as client:
    query = (
        client.awards.search()
        .grants()
        .agency("National Aeronautics and Space Administration")
        .keywords("asteroid")
        .fiscal_year(2024)
    )

    total = query.count()
    first = query.order_by("Award Amount", "desc").first()
```

`count()` and `.first()` are separate API operations. A configured `.limit()`
also bounds `count()` and `len(query)`, so those values agree with the number of
rows the bounded query can produce.

## Geographic filters

`.place_of_performance_locations(...)` and `.recipient_locations(...)` take one
dictionary per location. A congressional district is the bare district number,
such as `"01"`, alongside its state, not a combined `"WA-01"` string:

```python
with USASpendingClient() as client:
    district = (
        client.awards.search()
        .contracts()
        .agency("National Aeronautics and Space Administration")
        .place_of_performance_locations(
            {"country_code": "USA", "state_code": "WA", "district_current": "01"}
        )
        .fiscal_year(2024)
        .limit(10)
    )
```

Use `.place_of_performance_scope("domestic")` or `("foreign")` when the
question is domestic versus overseas work rather than a specific place. Foreign
performance has no state or district, so scope is the only way to select it.

## Account and classification filters

The search builder also supports award amounts, NAICS and PSC codes,
assistance listings, Treasury Account Symbols, object classes, program
activities, and Disaster Emergency Fund Codes. Treasury Account components take
a dictionary of the parts you want to match, so a single main account can be
isolated within an agency:

```python
with USASpendingClient() as client:
    science = (
        client.awards.search()
        .contracts()
        .agency("National Aeronautics and Space Administration")
        .treasury_account_components({"aid": "080", "main": "0120"})
        .fiscal_year(2024)
        .limit(10)
    )
```

DEF codes are reference data and can change as legislation is enacted. Discover
the API's current codes instead of maintaining a local list:

```python
with USASpendingClient() as client:
    def_codes = client.references.def_codes()
    for def_code in def_codes:
        print(def_code.code, def_code.title)
```

Pass the selected values to `.def_codes(...)`; constructing that search filter
does not perform another reference lookup.

Consult the [query reference](../reference/queries.md) for exact signatures and
the [upstream mapping](../usaspending-api/endpoint-mapping.md) for API context.

!!! warning "Large result sets"

    The default result limit protects callers from accidentally fetching very
    large searches. Narrow the query or use the
    [bulk download workflow](spending-and-downloads.md) when you need a full
    extract.
