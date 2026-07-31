# Limits and API differences

The wrapper deliberately rejects or calls out cases where USAspending's
endpoints do not share the same contract.

## Search endpoints are not interchangeable

- Award search returns one row per award and accepts only one award category.
- Global transaction search returns one row per action and accepts mixed
  categories.
- Award-scoped transactions use a different response shape from global
  transaction search.
- Subaward search reuses the award-search endpoint with a different spending
  level and result shape.

The library uses separate query builders rather than pretending these contracts
are identical.

## Result windows and limits

Global transaction search exposes at most the first 50,000 matching rows.
Iteration past that window raises `APIError`. Library `.limit()` and
`default_result_limit` settings may impose smaller bounds.

USAspending page sizes are also bounded. Query builders paginate automatically;
changing the client-side limit does not increase the upstream page size.

## Search and count filters can differ

The global transaction search endpoint supports `program_activities`, but its
count endpoint does not. With that filter present, iteration, `.all()`, and
`.first()` work; `.count()`, `len()`, indexing, and slicing raise
`ValidationError` rather than reporting a count for a different query. Note
that `list(query)` consults the length and therefore raises, while iterating
the same query in a `for` loop does not.

## Downloads accept fewer filters

The server-side download endpoint does not implement every advanced-search
filter. The library forwards the search filters but emits a warning for known
unsupported keys such as `object_classes`; USAspending ignores that key, so the
export is not narrowed by it.

## Missing values and zero

Optional model properties return `None` when the upstream row contains no
value. Numeric zero remains `Decimal("0.00")`, and negative obligations remain
negative.

## Live data drift

USAspending data is updated and corrected after initial publication. Example
counts and amounts are illustrative. Applications should not treat a value
shown in documentation as a permanent expected result.

## Source of truth

These pages explain wrapper behavior. For request and response schemas, consult
the linked upstream contract from [Endpoint mapping](endpoint-mapping.md).
