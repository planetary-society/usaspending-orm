# Query execution

Query builders separate request construction from execution.

## Lazy construction

Filter, sort, and limit calls modify the builder without making an HTTP
request:

```python
query = (
    client.awards.search()
    .contracts()
    .agency("National Aeronautics and Space Administration")
    .fiscal_year(2024)
    .limit(25)
)
```

The request begins when code:

- iterates over the query;
- calls `.all()`, `.first()`, or `.count()`;
- calls `len(query)`;
- indexes or slices the query;
- evaluates its truth value.

## Pagination

Iteration requests pages as needed and stops when the API is exhausted or a
configured bound is reached. Query builders expose list-like operations, but
they do not pre-load the entire result set.

`.all()` materializes the bounded query into a list. Prefer iteration when
streaming pages is sufficient.

Slices support positive and negative steps. Within a stepped slice, each
visited page is fetched once, even when several selected records share it.

## Count consistency

`count()` uses a companion endpoint when USAspending provides one. Library
limits are applied to the reported value so these expressions agree for a
bounded query:

```python
query = client.awards.search().contracts().fiscal_year(2024).limit(10)

query.count()
len(query)
len(query.all())
```

Some upstream search and count endpoints accept different filters. When a
correct count cannot be requested, the library raises `ValidationError` rather
than returning a misleading number.

Subaward counts use the grouped count endpoint with the same filters as the
search, including the prime-award restriction. Counting does not download all
matching subaward rows.

## Immutable chaining

Fluent methods return a clone with the new filter, sort, or bound. A partly
built query can therefore be used as an immutable template:

```python
base = client.awards.search().contracts().fiscal_year(2024)
california = base.place_of_performance_locations(
    {"country_code": "USA", "state_code": "CA"}
)
```

After this call, `base` remains unchanged and `california` carries the added
location filter.

Repeated NAICS, hierarchical PSC, and TAS calls combine their `require` and
`exclude` lists. Combined size and depth limits are checked before execution.
Mixing simple PSC codes with hierarchical PSC restrictions raises
`ValidationError`, including when the formats appear in separate chained calls.
