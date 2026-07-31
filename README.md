# USASpending ORM

[![Tests](https://github.com/planetary-society/usaspending-orm/actions/workflows/test.yml/badge.svg)](https://github.com/planetary-society/usaspending-orm/actions/workflows/test.yml)
[![PyPI](https://img.shields.io/pypi/v/usaspending-orm.svg)](https://pypi.org/project/usaspending-orm/)
[![Python](https://img.shields.io/pypi/pyversions/usaspending-orm.svg)](https://pypi.org/project/usaspending-orm/)

USASpending ORM is a typed, ORM-style Python interface to the
[USAspending.gov API](https://api.usaspending.gov/). It provides fluent query
builders and navigable models for federal awards, transactions, recipients,
agencies, spending summaries, Treasury Account Symbols, and bulk downloads.

The library is maintained by [The Planetary Society](https://www.planetary.org/).

## Why use it?

- Express complex USAspending searches through chainable Python methods.
- Work with normalized models, `date` values, and exact `Decimal` amounts.
- Navigate from awards to recipients, agencies, transactions, funding, accounts,
  and subawards.
- Retain the original API response through each model's `.raw` property.
- Use built-in pagination, retries, rate limiting, optional caching, and result
  safeguards.

No API key is required.

## Installation

```console
python -m pip install usaspending-orm
```

Requires Python 3.9 or newer.

## Quickstart

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
        amount = award.total_obligation or 0
        print(f"{award.award_identifier}: {award.recipient.name} - ${amount:,.2f}")
```

Queries are lazy. Building the chain makes no request; iteration, `.first()`,
`.all()`, `.count()`, `len(query)`, indexing, and truth-value testing execute
the appropriate USAspending operation.

## Documentation

The full documentation covers:

- [installation and core concepts](docs/getting-started/installation.md);
- [award and transaction searches](docs/guides/search-awards.md);
- [sessions, lazy loading, caching, and production use](docs/guides/production.md);
- [generated Python API reference](docs/reference/client.md);
- [mappings to canonical USAspending endpoints](docs/usaspending-api/endpoint-mapping.md);
- [known upstream limits and contract differences](docs/usaspending-api/limitations.md).

The repository includes Read the Docs configuration for the published site.

## Development

```console
git clone https://github.com/planetary-society/usaspending-orm.git
cd usaspending-orm
uv sync --locked --group docs

uv run pytest -q
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
uv run --group docs mkdocs build --strict
```

Integration tests make live USAspending requests and run separately:

```console
uv run pytest -m integration -q
```

Preview the documentation site locally with `uv run --group docs mkdocs serve`.

> **Note for contributors**
>
> Documentation examples are enforced, not just reviewed. `tests/test_documentation.py`
> compiles every fenced `python` block under `docs/`, checks that method names cited in
> prose exist on the public API, and executes most blocks against the live API under the
> `integration` marker. Adding or removing an example changes the runnable count, so
> update `_EXPECTED_RUNNABLE_BLOCKS` in the same change.
>
> The public API surface is snapshot-tested. When a deliberate change adds, removes, or
> alters a public callable, regenerate the fixture and review the diff:
>
> ```console
> USASPENDING_REGEN_API_SURFACE=1 uv run pytest tests/test_public_api_surface.py
> ```
>
> The published site builds from `.readthedocs.yaml`. To activate hosting: import
> `planetary-society/usaspending-orm` in Read the Docs, use `usaspending-orm` as the
> project slug, and enable pull-request builds. Keep `latest` as the default until a
> release tag contains the docs configuration, then make `stable` the default
> user-facing version while retaining `latest` for `main`.

## Project status

The project is in beta. USAspending itself changes over time, and live federal
data is revised as agencies submit corrections. Counts and values shown in
examples should not be treated as permanent fixtures.

See [CHANGELOG.md](CHANGELOG.md) for release history and compatibility notes.

## License

USASpending ORM is released under the [MIT License](LICENSE).
