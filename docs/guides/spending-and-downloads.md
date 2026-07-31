# Spending summaries and bulk downloads

Use aggregation queries when you need grouped totals. Use server-side downloads
when you need many underlying records.

## Aggregate spending

```python
from usaspending import USASpendingClient

with USASpendingClient() as client:
    recipients = (
        client.spending.search()
        .by_recipient()
        .contracts()
        .agency("National Aeronautics and Space Administration")
        .fiscal_year(2024)
        .limit(10)
    )

    for row in recipients:
        print(row.name, row.amount)
```

The spending resource also supports geography-oriented groupings such as state
and congressional district, through `.by_state()` and `.by_district()`. Grouping
and filter methods can be chained in any order, so a shared base query can pick
its grouping last:

```python
with USASpendingClient() as client:
    base = (
        client.spending.search()
        .agency("National Aeronautics and Space Administration")
        .spending_level("transactions")
        .fiscal_year(2024)
        .place_of_performance_locations({"country_code": "USA", "state_code": "WA"})
    )

    statewide = base.by_state().first()
    print(statewide.name, statewide.amount)
```

`.spending_level(...)` controls what is being summed and defaults to
`"transactions"`, which counts every modification separately. Use `"awards"` to
group by distinct award instead, or `"subawards"` for pass-through spending. The
level changes the totals without changing the shape of the result, so set it
deliberately.

Aggregation results are typed models rather than prime award records. A grouping
that matches nothing yields no rows, so `.first()` returns `None`; guard it
before reading `.amount`.

## Queue a search download

USAspending creates bulk exports asynchronously:

```python
from usaspending import USASpendingClient

with USASpendingClient() as client:
    query = (
        client.awards.search()
        .contracts()
        .agency("National Aeronautics and Space Administration")
        .keywords("asteroid")
        .fiscal_year(2024)
    )

    job = client.downloads.search(
        query,
        spending_level=["awards", "transactions"],
        file_format="csv",
        destination_dir="./exports",
    )

    files = job.wait_for_completion()
    for path in files:
        print(path)
```

`wait_for_completion()` blocks until the server finishes, then downloads the
archive and extracts it, returning the extracted file paths. It writes to
`destination_dir`, or to the current working directory when that argument is
omitted. The same paths remain available afterward as `job.result_files`.

To poll without blocking, call `job.refresh_status()` and read `job.state` and
`job.is_complete`.

!!! warning "Downloads can be large"

    Only the query's filters are forwarded. A `.limit()` set on the query does
    not bound the export; pass `limit=` to `downloads.search()` for that, or
    narrow the filters before queueing a broad search.

## Download one award

```python
with USASpendingClient() as client:
    award = client.awards.find_by_award_id("80GSFC18C0008")
    job = award.download(destination_dir="./exports")
    job.wait_for_completion()
```

`award.download()` covers contracts, grants, and IDVs. Other award types raise
`NotImplementedError`. To queue a download from an ID you already hold, use
`client.downloads.contract(...)`, `.assistance(...)`, or `.idv(...)`, which
each take the award's generated unique ID rather than its human-readable award
identifier.

!!! note "Filter differences"

    The download endpoint does not accept every advanced-search filter. The
    library warns when a filter such as `object_classes` cannot be represented
    in the download request.
