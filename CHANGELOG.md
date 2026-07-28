# Changelog

All notable changes to the USASpending ORM library are documented here.
The format loosely follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and the project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

Internal simplification pass. Except where listed below, every change is
behavior preserving and the public API is unchanged.

### Added

- `Recipient.recipient_level`: which level of the recipient hierarchy a record
  describes, as `"C"` (child), `"P"` (parent) or `"R"` (no parent). The API
  reports it on every recipient payload and the library previously dropped it.
  Since the same entity can exist at several levels, each a separate record with
  its own totals, and since a multi-level ID is reduced to one level on
  construction, this reports which record is in hand without parsing the ID.

  To fetch a specific level, pass an ID that already carries the suffix:
  `client.recipients.find_by_recipient_id("<hash>-R")` is used as-is. Only the
  multi-level `"<hash>-['C', 'R']"` form is reduced, so an explicit suffix is
  the supported way to opt into a level other than the default.

### Changed

- Date parsing reads the shape the API actually sends about 11 times faster.
  Every date the library returns passes through one converter, which worked down
  a list of seven `strptime` formats until one matched. The first entry is the
  plain `YYYY-MM-DD` that accounts for 92 of the 94 date values in the captured
  API responses, and reading that through `date.fromisoformat` instead takes
  0.18 us rather than 2.06 us. Where it shows up is per row: reading
  `action_date` across a full 5000-transaction page falls from 11.0 ms to
  1.7 ms.

  This is CPU only. No request count changes, no value changes, and every format
  the converter accepted before is still accepted, verified on Python 3.9, 3.10,
  3.11 and 3.12. The fast path is deliberately pinned to the exact `YYYY-MM-DD`
  shape rather than handed the string outright, because Python 3.11 widened
  `date.fromisoformat` to accept `20250829` and `2025-W35-5`, which the 3.9 floor
  refuses and USAspending never sends. Accepting those on a new interpreter and
  not an old one would make the library's behavior depend on the Python it runs
  on, which is worth more than either form.

- `client.tas.agencies` returns a `TASAgenciesQuery` instead of `list[Agency]`,
  matching the two levels below it in the same tree: `Agency.federal_accounts`
  and `FederalAccount.tas_codes` are both queries. Iteration, `len()`, indexing
  and slicing work unchanged, so most code needs no edit; call `.all()` where a
  real list is required, and note that `== []` no longer works as an emptiness
  check. In exchange the level is fetched once, filtering costs no further
  requests, and there is no shared list for one caller to corrupt for the next.
  `TASAgenciesQuery` is now exported, with `code()`, `codes()` and
  `description()` filters that were previously unreachable.

- `Agency.federal_accounts` and `FederalAccount.tas_codes` fetch their level of
  the TAS tree once per model instead of once per read. Both return the same
  query type as before and stay lazy, so no call site changes; what changes is
  the request count.

  The saving is large because these levels nest. Walking an agency's 16 accounts
  and reading each one's TAS codes used to cost 33 requests; it now costs 17, the
  floor set by the API's one-request-per-level shape. Filtering costs nothing
  extra, since it happens in memory: the same walk with three `fiscal_year()`
  filters per account fell from 49 requests to the same 17, and three
  `agency.federal_accounts.fiscal_year(...)` calls, whose predicate reads every
  account's codes, fell from 99 to 17.

  The tradeoff is staleness. A long-lived `Agency` keeps reporting the accounts
  it first saw, where before every read went to the API. Construct a fresh model
  to pick up changes, or `del agency._federal_accounts_level` to drop just the
  cache. `reattach()` also discards these caches, since the models in them are
  bound to the client being replaced.

  Two caveats worth stating plainly. This cache is not the one `config` describes:
  `cache_enabled` is off by default and governs HTTP responses with a TTL, while
  this one is always on, per model instance, and has no TTL, so turning response
  caching off does not make these two properties re-read. And what was previously
  reallocated per read is now retained for the parent model's lifetime, about
  0.2 MB for a 16-account agency with its codes, so a walk over many agencies
  should drop each one as it goes rather than accumulate them.

Title casing now emits a `UserWarning` when `special_cases.yaml` exists but
cannot be read as a list, where before the problem went only to the log and was
invisible in practice: names were still returned, just mis-cased. It still
degrades to no special casing rather than raising, because casing runs inside
`__repr__` on several models and a cosmetic problem must not break debuggers,
logging or error messages. Anyone wanting it fatal can escalate with
`-W error::UserWarning`. A merely absent file warns only in the log, since an
installation can legitimately lack it.

Optional money and string getters now return `None` when the API reports no
value, instead of a fabricated `Decimal("0.00")` or `""`. A value the API
actually reports as zero still returns `Decimal("0.00")`, so callers can finally
tell "this award has no such figure" from "this figure is zero" -- previously
both produced `Decimal("0.00")` and the distinction was unrecoverable.

Affected properties:

- `Award.total_obligation`, `Award.award_amount`
- `Award.covid19_obligations`, `Award.covid19_outlays`
- `Award.infrastructure_obligations`, `Award.infrastructure_outlays`
- `AwardAccount.total_transaction_obligated_amount` and its alias
  `AwardAccount.obligated_amount`
- `Funding.transaction_obligated_amount` and `Funding.gross_outlay_amount`,
  which returned `Decimal("0.00")` while declaring `Optional[Decimal]`. This
  also resolves a contradiction: `Grant.transaction_obligated_amount` already
  returned `None` for the same property name.
- `Location.zip5` and `Location.district`, which already declared
  `Optional[str]` while returning `""`
- `Award.type`, its alias `Award.award_type_code`, and `Award.type_description`,
  which also declared `Optional[str]` while returning `""`. `Contract.contract_award_type`
  follows, since it delegates to `type_description`. Award-type dispatch is
  unaffected: `create_award` reads the raw payload, not these properties.

**Migrating.** Any f-string or arithmetic on these needs a fallback:

```python
# Before
print(f"${award.total_obligation:,.2f}")
# After
print(f"${award.total_obligation or 0:,.2f}")
```

Comparisons against zero change meaning deliberately: `award.covid19_obligations
== 0` was true for every award without COVID-19 funding and is now false, while
`is None` identifies exactly those awards. Measured against live data, the four
COVID-19 and infrastructure properties are the ones that move in practice: they
are absent for all six awards in the golden-master suite, where the library
previously reported `Decimal("0.00")` for each, plus
`Funding.transaction_obligated_amount` on the live funding record.
`total_obligation`, `award_amount`, `zip5` and `district` were unchanged on that
data, because the API does report them.

Fourteen documentation examples that formatted money with `:,.2f` were given the
same `or 0` fallback, since copying them unchanged would raise `TypeError` on a
record with no reported figure. Four of those were already broken before this
release, formatting properties that were already `Optional`.

Three documentation examples referenced properties that do not exist and were
corrected while sweeping: `client.py` used `award.amount` and
`award.recipient_name` (neither is defined on `Award`; they are now
`award.total_obligation` and `award.recipient.name`), and the IDV child-award
examples in `idv.py` and `idv_child_awards.py` used `child.obligated_amount`,
which no `Award` subclass defines, now `child.award_amount`.

`Award.award_identifier` deliberately still returns `""` rather than `None`. It
is annotated `-> str`, so unlike `Location.zip5` there was no `Optional`
annotation to reconcile it with, and changing it would be a break with no
consistency argument behind it.

### Fixed

- `reattach(recursive=True)` now reaches every nested model that holds the client.
  It recognized only lazy-loading models, so `AwardAccount`, `FederalAccount`,
  `Funding`, `SubAward` and `TreasuryAccountSymbol` were silently stepped over and
  kept a weak reference to the outgoing client. Reading one after that client was
  collected raised `DetachedInstanceError`, including for a model the caller was
  still holding, such as a `TreasuryAccountSymbol` taken from
  `account.tas_codes`.

  Holding a client, not loading lazily, is what makes a model need rebinding, so
  that is what the walk now tests. It also means a recursive reattach rebinds the
  models inside a cached level in place rather than discarding the level: a
  16-account agency with its TAS codes now costs no requests after a reattach,
  where discarding cost 17. A non-recursive reattach still discards those caches,
  since it deliberately leaves nested models alone and they would otherwise serve
  a client on its way out.

- `award.transactions` no longer reports a count that disagrees with what it
  yields. `since()` and `until()` filter in memory, because the endpoint has no
  date filter, but the count came from the API or from summing raw response rows,
  so it included transactions the caller would never see. On a three-transaction
  award with `since("2024-01-01")` matching two, `count()` and `len()` both said
  three, `len(query[0:len(query)])` disagreed with `len(query)`, and `query[-1]`
  raised `IndexError` because the negative index was offset from the unfiltered
  total. `count()`, `len()` and iteration now all report two, the slice agrees with
  `len()`, and `query[-1]` returns the last matching transaction. `bool(query)` and
  `first()` agree too: an in-memory bound now narrows the results rather than the
  fetch, so `limit(1)` means one matching row instead of one row that may then be
  discarded.

- `if query:` no longer costs a full pagination. With `__len__` defined and no
  `__bool__`, truthiness fell through to a count. On the five builders whose count
  comes from paging, that walked every page to settle a single bit: measured on 250
  transactions across 3 pages, `bool(query)` was 3 requests and is now 1. It reads
  one row via `first()`. The queries that hold their rows in memory, such as
  `client.tas.agencies`, answer from their own count instead, which for them is
  cheaper than reading a row and does not re-request the level.

- `query.limit(0).first()` returned a row, contradicting `query.limit(0).all()`
  and `len(query.limit(0))`, which both reported nothing. `first()` asked for
  `limit(1)`, overriding the caller's zero. It now respects it, which is also what
  makes the new `__bool__` correct for a zero-limit query.

- `.all()` no longer spends an API request on a count it discards. `list(self)`
  asks an object for a length hint, which called `__len__` and so `count()`,
  sending a request purely to size the list it was about to build, then throwing
  the answer away. Every `.all()` in the library paid it, so
  `client.awards.search().contracts().all()` sent two requests where the
  equivalent loop sent one. `all()` now iterates instead of handing itself to
  `list()`, so it asks for no hint.

  On the five builders with no count endpoint, the cost was not one request but a
  second complete pass over every page, because their count is produced by paging
  the whole result set: award funding, spending search, IDV child awards, unscoped
  subaward search, and transactions whenever a date filter is set. Measured on 250
  transactions across 3 pages, `.all()` went from 6 requests to 3, and the saving
  grows with the result set. For a filter-tree level, which needs no extra
  request, the same change halved the in-memory work: 3.6 ms to 1.8 ms over 2000
  rows.

  `len(query)` still calls the count endpoint, as it must, and so does everything
  that consults the hint: `list(query)`, `tuple(query)`, `sorted(query)`,
  `[*query]`, `f(*query)`, and `bool(query)` -- a bare `if query:` is a count, and
  on those five builders a full pagination. None of it can be made cheap while
  `len()` remains meaningful, since Python checks `__len__` before
  `__length_hint__`. Prefer `.all()` or a plain loop; `set(query)`, `sum(...)`,
  `in` and comprehensions were never affected. The 13 docstring examples that
  taught `list(...)` now show `.all()`.

- `client.recipients.find_by_id()` no longer addresses the wrong record for a
  recipient ID carrying several levels, such as `"<hash>-['C', 'R']"`.
  Normalization was implemented twice with algorithms that disagreed:
  `Recipient` kept the first level in the list while the recipient query
  preferred `R`, so the same raw ID addressed `<hash>-C` through a model and
  `<hash>-R` through the finder. Six such IDs appear in the captured API
  fixtures, so this reached real data.

  Both paths now avoid the `R` level whenever another is available. Measured
  against the live endpoint for all six of those IDs, the `R` record reports
  less spending than its sibling and reports flat zero in four of the six, with
  `parent_id`, `parent_name` and `parents` all null. One example reports $24.6M
  over 109 transactions at `-C` and $0 over 0 transactions at `-R`, so the
  finder could previously report a $1.3B recipient as having no spending and no
  parent at all.

- `client.spending.search().recipient_id()` also normalizes its argument. It
  validated the ID but passed it through unchanged, so a multi-level ID copied
  out of `raw()` or off the USAspending website produced a filter the API could
  not match.

- Iterating `idv.child_awards` no longer raises `AttributeError: 'str' object has no attribute 'get'` when reading `funding_agency`, `awarding_agency`, `funding_subtier_agency` or `awarding_subtier_agency`. The `/idvs/awards/` endpoint reuses those keys for a plain agency-name string rather than an agency record, and the model accepted any truthy value there. All four now return `None` for such records, and the name remains available via `raw()`. Present in 0.7.3.
- `Award._load_agency_data` raises `ValidationError` rather than a bare `ValueError` for an invalid `agency_type`, matching every other agency-type check in the library. `ValidationError` subclasses `ValueError`, so existing `except ValueError` handlers are unaffected.
- `Transaction` instances no longer compare equal to one another regardless of their data. The class was declared `@dataclass` with no fields, which generated an `__eq__` comparing empty tuples, so any two transactions were equal and `__hash__` was `None`, making them unhashable. They now compare by identity, like every other model, and can be used in sets and as dict keys.
- `FederalAccount.count` no longer fires an API request when the count is already present in the response, and repeated access now costs at most one request rather than one per access. The fallback that counts TAS codes was passed as a default argument, which Python evaluates eagerly, so every access paid for a request whose result was then discarded.

### Removed

- `usaspending.utils.formatter` is split into `usaspending.utils.dates`,
  `usaspending.utils.numbers` and `usaspending.utils.textcase`. Every symbol it
  held was internal, absent from `__all__` and from the README, so there is no
  compatibility shim; anything importing it directly was reaching past the public
  API. The casing machinery is now one cohesive module, which is the boundary a
  future plugin would lift.
- `current_fiscal_year()`, which had no callers. Nothing in the library used it,
  it was not exported, and it had no test; the endpoints that document defaulting
  to the current fiscal year are defaulted server-side. It briefly gained a fix in
  this release for reading the clock twice, which was a fix to dead code.

- `Agency.__init__`'s third parameter, `subtier_data`. It was stored on the
  instance and never read: `Agency` exposes no subtier property, and subtier
  data has its own model, `SubTierAgency`. Only one caller passed it, and the
  value was discarded. Callers who passed a third argument should drop it; the
  resulting `Agency` is identical either way. Use `Award.funding_subtier_agency`
  or `Award.awarding_subtier_agency` to reach subtier data.

## [0.7.3] - 2026-07-05

### Added

- `AwardsSearch.object_classes(*codes)`: filter awards by federal object class codes (per Office of Management and Budget Circular A-11) on the `/search/spending_by_award/` and `/search/spending_by_award_count/` endpoints. Pass codes such as `"10"` or `"252"`, not names; multiple codes use OR logic.
- `SubAwardsSearch.object_classes()` raises `ValidationError`. The USASpending API accepts the `object_classes` filter for award searches only and returns HTTP 422 when it is combined with `spending_level=subawards`.
- `client.downloads.search()` emits a `UserWarning` when the query contains an `object_classes` filter, because the `/api/v2/download/search/` endpoint drops the key. The filter is still forwarded unmodified.
- Known upstream limitation as of 2026-07-05: the production API accepts `object_classes` but the rollout is incomplete. The search endpoint returns zero results for any object class, the count endpoint does not narrow, and the subawards rejection is not yet enforced server side. The filter should begin returning data once USAspending finishes deploying the feature and populating its award index.
- `tests/test_readme_examples.py`: integration tests that extract the README's Python code blocks and execute the runnable ones verbatim against the live API, so broken or rotted examples fail mechanically. A network-free guard in the default suite catches extraction drift. The live `client` fixture moved to `tests/conftest.py` and is now shared with `tests/test_integration.py`.

### Documentation

- Corrected the `api-docs-links.md` subawards entry: `SubAwardsSearch` POSTs `/api/v2/search/spending_by_award/` with `subawards=true` and `spending_level=subawards` (inheriting `AwardsSearch`) rather than calling `/api/v2/subawards/`.
- Added missing `api-docs-links.md` entries for `/api/v2/idvs/awards/` (IDV child awards) and the TAS filter-tree endpoints (`/api/v2/references/filter_tree/tas/` and its `{toptier_code}/` and `{toptier_code}/{federal_account}/` variants).
- An upstream API compatibility review of USASpending API releases from April through June 2026 found no breaking changes for this library. The 0.7.2 release already handles the `spending_by_award` Pydantic migration (HTTP 422 validation errors), the `program_activities` filter rename, and the new F001 through F010 assistance type codes.
- Revalidated all README examples against live USAspending data. Fixed two broken chains (`location.full_address` is actually `location.formatted_address`; a subaward's place of performance is on the subaward, not its recipient), refreshed stale sample outputs, and added examples for the `client.spending` category rollups and the list-style `len(query)` interface.

## [0.7.2] - 2026-06-05

### Added

- `client.downloads.search(query, ...)` backed by the new `/api/v2/download/search/` endpoint, which bundles award, transaction, and subaward data into a single download built from an awards search query. Supports `file_format`, `spending_level`, `columns`, and `limit`.
- `QueryBuilder.to_filters_payload()`: public accessor returning the assembled API `filters` object for a query without executing a search.

### Changed

- HTTP 422 (Unprocessable Entity) validation responses are now surfaced as `APIError` with the response detail instead of a generic `HTTPError`. This aligns with the USASpending API's move to Pydantic request validation on `/search/spending_by_award/`.

### Deprecated

- `program_activity()` is deprecated and now forwards to `program_activities()`, emitting a `DeprecationWarning`. The USASpending API removed the `program_activity` filter from `/search/spending_by_award/` in favor of `program_activities`. Existing calls continue to work; integer codes are forwarded as string `code` values.

## [0.7.1] - 2026-04-16

### Added

- Public export of `DetachedInstanceError` so callers can `from usaspending import DetachedInstanceError` as documented in the README.
- `config.allowed_download_hosts`: an allow-list of hostnames the library will fetch binary downloads from. Defaults to `{"api.usaspending.gov", "files.usaspending.gov"}`.
- `config.validate()` now rejects malformed `base_url`, CR/LF in `user_agent`, and empty `cache_dir`.

### Changed

- `ValidationError` now inherits from both `USASpendingError` and the built-in `ValueError`. Callers that previously caught `ValueError` for invalid parameters continue to work unchanged; new code can catch the library-specific `ValidationError`.
- `RateLimiter` now raises `ValidationError` (rather than a bare `ValueError`) for invalid `max_calls`/`period` arguments. Non-breaking due to the dual inheritance above.
- `RecipientsResource.find_by_recipient_id` is now annotated as non-Optional. This matches its long-standing behavior of raising on miss via the direct-ID lookup path; runtime behavior is unchanged. `find_by_duns` and `find_by_uei` remain Optional because they use the search-delegation path.
- `Agency.get_obligations` return annotation corrected from `float | None` to `Decimal | None` to match actual runtime type.
- `Agency.total_obligations` now applies `Decimal` coercion to stored values to match its declared return type.
- `TransactionsSearch._award_id` and `FundingSearch._award_id` annotated as `str | None` rather than `str` (they are always `None` until set).
- `time_period()` now rejects date ranges where `end_date` is earlier than `start_date`.

### Fixed

- `to_date()` now extracts the `date` portion from `datetime` inputs instead of passing them through unchanged.
- `IDVChildAwardsSearch._clone()` no longer silently drops `_filter_objects`, `_max_pages`, `_order_by`, and `_order_direction` when chaining.
- `SubAwardsSearch._clone()` now delegates to `super()._clone()` so base-class state changes propagate.
- `AwardAccountsQuery._clone()` no longer copies a stale `_cached_count` across filter changes.
- `Agency.latest_action_date` no longer crashes when the award-summary endpoint returns no data.
- `round_to_millions()` cleaned up redundant disjunct in threshold check.
- Removed unused `DEFAULT_KEEP_UPPERCASE` set, which also contained a latent missing-comma bug that concatenated two entries.
- Fixed malformed `Raises:` block in `AwardResource.find_by_generated_id` docstring.
- `Agency.id` was missing its return-type annotation.

### Security

- Binary downloads (`_download_binary_file`) now require `https` and a hostname on `config.allowed_download_hosts`, mitigating SSRF if API responses are tampered with.
- File-backed cache directory is now created with `0700` and tightened to `0700` if it already exists with looser bits. Protects the pickle-backed cache on shared hosts.
- ZIP extraction creates the extract directory with `0700`, detects absolute paths with stdlib `posixpath.isabs` / `ntpath.isabs` (covers Windows drive letters and UNC prefixes), and uses `normpath`-based prefix comparison for traversal detection.

### Removed

- Dead code: `get_past_fiscal_years`, `custom_titlecase_callback`, `parse_agency_type`, `parse_agency_tier`, `QueryBuilder._fetch_page`, empty `AwardsSearch.__init__`, redundant `AwardsSearch._clone` override, unreachable `try/except` in `_derived_award_identifier`.

## [0.7.0] - 2026-04-12

Previous release. See git history for details.
