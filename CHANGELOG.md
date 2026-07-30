# Changelog

All notable changes to the USASpending ORM library are documented here.
The format loosely follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and the project adheres to [Semantic Versioning](https://semver.org/).

## [0.9.0] - 2026-07-30

Adds the global transaction search: `client.transactions.search()` covers the
`/search/spending_by_transaction/` endpoint with the full fluent filter set,
mixed award-type categories, exact bucketed counts, and a `Transaction` model
that reads both of the API's row shapes.

**Breaking changes**

- `TransactionsSearch` is renamed to `AwardTransactionsSearch`. The freed name is
  reused in this release for the new global `/search/spending_by_transaction/`
  builder, so code importing `TransactionsSearch` directly keeps importing
  cleanly but gets a different class rather than an `ImportError`. No
  deprecation alias is provided. `client.transactions.award_id()` and
  `award.transactions` are unchanged in both behavior and return value; only the
  class and module names moved.

- `Transaction.transaction_amount` and its alias `amt` now return the first
  nonzero of `federal_action_obligation`, `face_value_loan_guarantee` and
  `original_loan_subsidy_cost`, and return the zero when every figure the row
  carries is zero. Previously a zero obligation read as no value at all, so a
  genuine zero-dollar transaction was indistinguishable from a row carrying no
  amount, and a loan row, which reports a zero obligation with the real figure
  in the loan fields, reported nothing. Negative figures such as deobligations
  are preserved rather than skipped over. `amt is None` used to be true for
  every zero-dollar transaction and is now true only for a row carrying none of
  the three fields, so an `is None` check standing in for "no money moved"
  needs `not amt` instead, and loan rows now report their face value, which
  changes any total taken over a loan result set. Note that USAspending.gov's
  own internal "pragmatic obligation" convention uses the subsidy cost, not
  the face value, as a loan transaction's budgetary figure; this library
  reports the face value the website displays, and
  `original_loan_subsidy_cost` remains directly readable for budgetary totals.

### Added

- `client.transactions.search()`, returning the new `TransactionsSearch` query
  builder over `/search/spending_by_transaction/`. It searches every
  transaction the API holds rather than the transactions of one award, and
  takes the same fluent filters the award search takes: `keywords()`,
  `agency()`, `time_period()` and `fiscal_year()`, the location, code and
  amount filters, plus `order_by()` over the endpoint's sort fields. An
  `award_type_codes` filter is required, and unlike the award search this
  endpoint accepts codes from more than one category at once, so
  `.contracts().grants()` is a single valid query where the same chain on
  `client.awards.search()` raises `ValidationError`. `count()` and `len()` read
  `/search/spending_by_transaction_count/`, summing the buckets of the
  categories the query selected. `TransactionsSearch` is exported from
  `usaspending` and `usaspending.queries`.

- `Transaction` reads both row shapes the API sends: the snake_case keys of the
  award-scoped `/transactions/` listing and the display-name keys of the global
  search (`"Action Date"`, `"Transaction Amount"` and the rest). The existing
  properties gained the second spelling, and the search rows carry fields the
  award-scoped listing never had: `award_internal_id`,
  `generated_unique_award_id`, `award_identifier`, `recipient_name`,
  `recipient_uei`, `recipient_id`, the four agency-name properties,
  `issued_date`, `last_date_to_order`, `naics_code`, `naics_description`,
  `psc_code`, `psc_description`, `cfda_title`, `def_codes`,
  `recipient_location` and `place_of_performance`. `id` is `None` for a global
  search row, which identifies only the parent award, and
  `transaction_description` is the preferred name for what `award_description`
  has always returned. Every raw row key also has a getter under its
  snake_cased name (`award_id`, `mod`, `award_type`, `loan_value`,
  `subsidy_cost`, `description`, `primary_place_of_performance`, `amount`),
  aliasing the normalized helpers, with the exceptions documented in the
  model: agency names live under `*_agency_name`, dict-valued classifications
  under their scalar helpers, and the server's award identifiers under
  `award_internal_id` and `generated_unique_award_id`.

### Known limitations

- `TransactionsSearch` is bounded by the API's 50,000-row result window.
  Iterating past that point raises `APIError` rather than truncating silently.
  Narrow the filters, set `limit()`, or use `client.downloads` for larger
  result sets; `count()` is not subject to the window.

- With a `program_activities()` filter set, `TransactionsSearch.count()` and
  `len()` raise `ValidationError`: the count endpoint silently ignores that
  filter while the search endpoint honors it, so passing it through would
  report a confidently wrong count. `list(query)`, indexing and slicing
  consult the count and so raise too; iteration, `all()`, `first()` and
  `bool()` need no count and work regardless.

## [0.8.0] - 2026-07-28

Mostly refactoring internals to DRY the codebase and standardize the query interface.
It now keeps one set of promises everywhere: `count()`, `len()`, iteration, indexing, slicing and
truthiness agree under the bounds you set. Adding CI tests to verify compatability for Pythons 3.9 - 3.14.

**Breaking changes**

- Optional money and string getters return `None` when the API reports no
  value; a reported zero is still `Decimal("0.00")`. Format with a fallback:
  `f"{award.total_obligation or 0:,.2f}"`.
- `count()` honors `limit()` and `max_pages()` on every query. Read the server
  total by counting before bounding (i.e. it will never return a count greater
  that your set limit).
- A lazy load that fails now raises instead of silently answering `None`
  forever. Only the API's "no such record" answers still read as absent data.
- `since()` and `until()` raise `ValidationError` for a pre-FY2008 bound (the lower
  limit for USASpending data) or given an inverted range instead of silently matching
  nothing useful.
- `order_by()` raises `ValidationError` on every builder for a direction other
  than `"asc"` or `"desc"`.
- `client.tas.agencies` returns a query object rather than a list. So `== []` no
  longer works as an emptiness check.
- A multi-level recipient ID now resolves away from the often-empty `R` level,
  changing which record `find_by_recipient_id()` returns for it.
- Removed without alias: the internal `usaspending.utils.formatter` module,
  module-level `logging_config.get_logger`, `Agency.__init__`'s unused
  `subtier_data` parameter, and `AgencyAwardSummary.find_by_id`.
- `Award.start_date` and `end_date` changed precedence for hand-built payloads
  carrying several date spellings; live API data is unaffected.

### Added

- `Recipient.recipient_level`: which level of the recipient hierarchy a record
  describes, as `"C"` (child), `"P"` (parent) or `"R"` (no parent).

- `usaspending.utils.current_fiscal_year()`: the federal fiscal year today
  falls in, as an int. October 1 opens the fiscal year named for the calendar
  year it ends in, so it reports 2026 on 2026-09-30 and 2027 on 2026-10-01.
  Relocated from the removed `usaspending.utils.formatter.current_fiscal_year`.

### Changed

- Optional money and string getters return `None` when the API reports no
  value, instead of a fabricated `Decimal("0.00")` or `""`. A value the API
  actually reports as zero still returns `Decimal("0.00")`, so callers can
  finally tell "this award has no such figure" from "this figure is zero";
  previously both produced `Decimal("0.00")` and the distinction was
  unrecoverable.

  Affected properties:

  - `Award.total_obligation`, `Award.award_amount`
  - `Award.covid19_obligations`, `Award.covid19_outlays`
  - `Award.infrastructure_obligations`, `Award.infrastructure_outlays`
  - `AwardAccount.total_transaction_obligated_amount` and its alias
    `AwardAccount.obligated_amount`
  - `Funding.transaction_obligated_amount` and `Funding.gross_outlay_amount`
  - `Location.zip5` and `Location.district`
  - `Award.type`, its alias `Award.award_type_code`, `Award.type_description`,
    and `Contract.contract_award_type`, which delegates to it. Award-type
    dispatch is unaffected: `create_award` reads the raw payload, not these
    properties.

  **Migrating.** Any f-string or arithmetic on these needs a fallback:

  ```python
  # Before
  print(f"${award.total_obligation:,.2f}")
  # After
  print(f"${award.total_obligation or 0:,.2f}")
  ```

  **This can break working code.** Comparisons against zero change meaning
  deliberately: `award.covid19_obligations == 0` was true for every award
  without COVID-19 funding and is now false, while `is None` identifies
  exactly those awards. On live golden-master data the COVID-19 and
  infrastructure properties and `Funding.transaction_obligated_amount` are the
  ones that move in practice; `total_obligation`, `award_amount`, `zip5` and
  `district` were unchanged there, because the API does report them.
  (`Grant.transaction_obligated_amount` already returned `None` for the same
  property name.) `Award.award_identifier` deliberately still
  returns `""`: it is annotated `-> str`, so there was no `Optional` contract
  to honor. Documentation examples that formatted money were given the same
  `or 0` fallback, and three examples referencing nonexistent properties
  (`award.amount`, `award.recipient_name`, `child.obligated_amount`) were
  corrected along the way.

- `count()` now honors `limit()` and `max_pages()` on every query, so
  `count()`, `len(query)` and `len(query.all())` agree under the bounds a
  caller sets. Which answer
  you got used to depend on how the endpoint reports a total: builders backed
  by a count endpoint or page metadata returned the server's figure whatever
  the caller asked for (`limit(3).count()` said 510 while the query yielded
  three rows), while builders that count by walking pages already stopped at
  the bound.

  **This can break working code** that used `count()` on a bounded query to
  read the server's total. Count before bounding: `search.count()` is the
  total under those filters, `search.limit(3).count()` is what the bounded
  query yields.

  `config.default_result_limit` is deliberately excluded from counts; it
  still caps iteration, so an unbounded query over more than 10,000 rows
  counts higher than it yields. That exclusion is itself a change for the
  builders whose count pages the result set: `len(award.funding)` on a result
  set larger than the default used to report the cap and now reports the true
  total. Bounds that forbid every result are answered without a request:
  `limit(0)` and `max_pages(0)` count 0 without touching the API, and for an
  in-memory query `bool(query.limit(0))` was True and is now False.

- A lazy load that fails no longer turns a model into a permanent source of
  `None`. `Agency` and `Recipient` reported every failure as absent data and
  latched, so one 500, one dropped connection or one read after
  `client.close()` left every lazy property answering `None` for the rest of
  the model's life, with no way to ask again.

  **This can break working code**, since a failure that used to be silent now
  raises. Only the API's answer that there is no such record is still reported
  as absent data: HTTP 400, 404 and 422 leave the model fetched and answering
  `None`, as does a model built with no id. Everything else now reaches the
  caller, including server errors, rate limits, connection errors, timeouts,
  and the `DetachedInstanceError` from a closed session. The model is left
  unfetched, so the next access retries, and a model whose load failed while
  detached now loads after `reattach()`. `Award` already raised, so it is
  unchanged.

  **Migrating.** Force the load once rather than guarding each property read,
  which would pay the full retry ladder per read (up to about 88 seconds of
  backoff at default settings):

  ```python
  try:
      agency.fetch_all_details()
  except (USASpendingError, requests.RequestException):
      logger.warning("Agency details unavailable")
      return None
  print(agency.mission)
  ```

- `award.transactions.since()` and `until()` now reject a bound the API cannot
  answer, matching what `time_period()` already enforced. A bound before
  FY2008 begins (2007-10-01) matched every row, so `since("1999-01-01")`
  looked like a filter and did nothing; an inverted range yielded no rows,
  indistinguishable from an award with no transactions in range. Both now
  raise `ValidationError`, checked by whichever of the two calls comes second.

  **This can break working code**: if you relied on an inverted range to
  select nothing, use `limit(0)` or skip the query; if you relied on a
  pre-FY2008 bound as a harmless no-op, clamp it to `2007-10-01` or drop it.
  Equal bounds still select that single day, and 2007-10-01 itself is valid.

- `order_by()` now validates its direction on every builder. Some builders
  already raised, the client-side queries accepted any string and silently
  sorted ascending, and the paginated searches passed the caller's spelling
  through to the API, so `order_by("amount", "sideways")` put
  `"order": "sideways"` on the wire. Every builder now raises
  `ValidationError` for a direction other than `"asc"` or `"desc"`.

  **This can break working code** that passed an unrecognized direction and
  relied on whatever came back: pass `"asc"` or `"desc"`. Which fields each
  builder accepts is unchanged; a few validator messages were unified in
  wording only, and `time_period()`'s error messages are unchanged.

- `client.tas.agencies` returns a `TASAgenciesQuery` instead of
  `list[Agency]`, matching `Agency.federal_accounts` and
  `FederalAccount.tas_codes`. Iteration, `len()`, indexing and slicing work
  unchanged, so most code needs no edit.

  **This can break working code** that requires a real list: call `.all()`,
  and use `if not query:` rather than `== []` as the emptiness check.

  In exchange the level is fetched once, filtering costs no further requests,
  and there is no shared list for one caller to corrupt for the next.
  `TASAgenciesQuery` is exported from `usaspending.queries`, with `code()`,
  `codes()` and `description()` filters that were previously unreachable.

- `Agency.federal_accounts` and `FederalAccount.tas_codes` fetch their level
  of the TAS tree once per model instead of once per read. No call site
  changes; the request count does. Walking an agency's 16 accounts and
  reading each one's TAS codes cost 33 requests and now costs 17, the floor
  set by the API's one-request-per-level shape; the same walk with in-memory
  `fiscal_year()` filters fell from 49 or 99 requests to the same 17.

  The tradeoff is staleness: a long-lived `Agency` keeps reporting the
  accounts it first saw. Construct a fresh model to pick up changes, or
  `del agency._federal_accounts_level` to drop the cache; a non-recursive
  `reattach()` also discards it, while a recursive one rebinds the cached
  models in place. This cache is not the one `config` describes:
  `cache_enabled` governs HTTP responses with a TTL, while this one is always
  on, per model instance, without one, so turning response caching off does
  not make these properties re-read. The retained level costs about 0.2 MB
  for a 16-account agency, so a walk over many agencies should drop each
  model as it goes.

- `Award.start_date` and `end_date` delegate to `period_of_performance`
  rather than keeping their own copy of the key list, which had drifted from
  the period model's. Three behaviors moved: where a payload carries both the
  flat and the nested spelling, the nested `period_of_performance` object now
  wins; the `"Period of Performance End Date"` alias, which no recorded API
  response carries, is no longer read; and `"Base Obligation Date"` now
  yields to `"Period of Performance Start Date"` where a payload carries
  both.

  **This can break working code** that feeds `Award` hand-built payloads and
  relies on any old precedence; read `award.raw` directly where the payload's
  spelling matters. Live API responses never carry disagreeing spellings.
  Cost moved rather than vanished: dates parse once on construction, so the
  first read of a single date is slower, repeat reads are roughly four times
  faster, and the crossover lands around six reads; against 0.7.3 every
  measured pattern is still faster.

- Date parsing reads the shape the API actually sends about 11 times faster.
  The converter tried seven `strptime` formats in order; plain `YYYY-MM-DD`
  accounts for nearly all API date values and now reads through
  `date.fromisoformat` behind a shape guard, taking 0.18 us rather than
  2.06 us. Reading `action_date` across a 5000-transaction page falls from
  11.0 ms to 1.7 ms. CPU only: no request or value changes, and every format
  accepted before is still accepted, verified on Python 3.9 through 3.14.
  The guard exists because 3.11 widened `fromisoformat` to accept forms the
  3.9 floor refuses, such as `20250829` and ISO week dates; without it the
  accepted set would depend on the interpreter.

- Title casing now emits a `UserWarning` when `special_cases.yaml` exists but
  cannot be read as a list, and another naming colliding entries (two
  spellings that lowercase to the same key), where before the problem went
  only to the log and names were silently mis-cased. It still degrades to no
  special casing rather than raising, because casing runs inside `__repr__`
  and a cosmetic problem must not break debuggers or logging; escalate with
  `-W error::UserWarning` if wanted. A merely absent file still warns only in
  the log, since an installation can legitimately lack it. The one duplicate
  entry in the shipped data file was removed.

- `to_int` reads numeric API fields leniently: a non-numeric value now yields
  `None` where the integer counts on `Funding`, `SubAward`,
  `TreasuryAccountSymbol` and `Award.subaward_count` previously raised
  `ValueError`.

- `SubAward.amount`'s return annotation is corrected from `float | None` to
  `Decimal | None` to match its actual runtime type; no runtime change.

### Deprecated

- `parse_date_string`'s `format_str` parameter, scheduled for removal in a
  future release. A non-default pattern still parses with the pattern the
  caller supplied, still raises `ValidationError` for a value it cannot read,
  and now emits a `DeprecationWarning`. Omitting the parameter, or passing
  its default, is unchanged and warns about nothing.

### Fixed

- Building a query's payload no longer mutates the filters that built it.
  When two filters serialized under one key, aggregation extended the first
  filter's own list in place, and since clones share filter objects, a
  derived query's payload grew on every build and corrupted its parent:
  `q1 = search().keywords("alpha")` followed by `q2 = q1.keywords("beta")`
  left `q1` sending `["alpha", "beta", "beta"]`. Affected chained `keywords`,
  `award_type_codes`, simple `psc_codes` and `treasury_account_components`
  filters.

- `client.recipients.find_by_recipient_id()` no longer addresses the wrong
  record for a recipient ID carrying several levels, such as
  `"<hash>-['C', 'R']"`. Normalization was implemented twice with algorithms
  that disagreed, and the finder's choice, `R`, is the record that reports
  little or no spending for most such IDs, so it could report a recipient
  with real spending as having none and no parent. Both paths now avoid the
  `R` level whenever another is available; to address a level explicitly,
  pass the suffix yourself (see `Recipient.recipient_level` under Added).
  `client.spending.search().recipient_id()` also normalizes its argument now,
  so a multi-level ID copied out of `raw` produces a filter the API can
  match.

- `award.transactions` no longer reports a count that disagrees with what it
  yields. `since()` and `until()` filter in memory, but the count came from
  the API, so it included transactions the caller would never see: `count()`
  and `len()` said three where iteration yielded two, slices disagreed with
  `len()`, and `query[-1]` raised `IndexError`. All of them now agree, and
  `limit(1)` means one matching row rather than one row that may then be
  discarded.

- A `Recipient` built directly from an award search result now reports its
  `uei` and `location`, which read only the nested spellings a detail
  response sends. `award.recipient.uei` worked because `Award` repaired the
  keys on the way past; `Recipient(row, client).uei` for the same row did
  not. `PeriodOfPerformance` had the same gap for `"Base Obligation Date"`.
  Both models now read every spelling of their own fields, and `Award` hands
  its payload over rather than reproducing the mapping; nested spellings
  still take precedence where a payload carries both.

- Indexing and slicing an in-memory query now read the limited collection:
  `agency.federal_accounts.limit(3)[:]` returned every account and
  `limit(3)[5]` returned a row; the slice now holds three rows and the index
  raises `IndexError`, agreeing with `len()` and `.all()`. Present in 0.7.3
  for every in-memory query; the new `tas.agencies` query made it visible.

- `Transaction` instances no longer compare equal regardless of their data. A
  fieldless `@dataclass` declaration generated an `__eq__` comparing empty
  tuples, so any two transactions were equal and none was hashable. They now
  compare by identity, like every other model, and can be used in sets and as
  dict keys.

- `Recipient.parents` returns a fresh list on each read, so sorting or
  popping the result no longer corrupts the model.

- Iterating `idv.child_awards` no longer raises
  `AttributeError: 'str' object has no attribute 'get'` when reading the four
  agency properties. The `/idvs/awards/` endpoint reuses those keys for a
  plain agency-name string, which the model accepted as a record; all four
  now return `None` there, with the name still available via `raw`. Present
  in 0.7.3.

- `reattach(recursive=True)` now reaches every nested model that holds the
  client. It recognized only lazy-loading models, so `AwardAccount`,
  `FederalAccount`, `Funding`, `SubAward` and `TreasuryAccountSymbol` were
  stepped over and could raise `DetachedInstanceError` after the old client
  was collected. The walk now tests for holding a client, and a recursive
  reattach rebinds cached TAS levels in place: a 16-account agency costs no
  requests after a reattach, where discarding the caches cost 17.

- `.all()` no longer spends an API request on a count it discards. `list()`
  asks for a length hint, which called `count()` purely to size the list, so
  every `.all()` paid one extra request, and on the five builders whose count
  pages the result set (award funding, spending search, IDV child awards,
  unscoped subaward search, and transactions with a date bound set), a second
  complete pass: 250 date-bounded transactions cost 6 requests, now 3.
  `len(query)` still counts, as must everything that consults the hint
  (`list(query)`, `tuple(query)`, `sorted(query)`, `[*query]`); `set(query)`,
  `sum(...)`, `in` and comprehensions were never affected. Prefer `.all()` or
  a plain loop. The 13 docstring examples that taught `list(...)` now show
  `.all()`.

- `if query:` no longer costs a full pagination. Truthiness fell through to
  `__len__`, which on the five paging-count builders walked every page to
  settle a single bit (250 date-bounded transactions: 3 requests, now 1). It
  reads one row via `first()`; in-memory queries answer from their own count
  instead.

- `FederalAccount.count` no longer fires an API request when the count is
  already in the response; the fallback was an eagerly evaluated default
  argument, so every access paid for a request whose result was discarded.

- `query.limit(0).first()` returned a row, contradicting `.all()` and
  `len()`. It now respects the zero, which is also what makes `__bool__`
  correct for a zero-limit query.

- The two date parsers now honor their documented contracts for unusable
  values. The strict filter parser raised `TypeError` from inside `strptime`
  for a non-string (most often a threaded-through `None`) rather than the
  promised `ValidationError` naming the field; the lenient API-payload
  converter could leak the same `TypeError` rather than answering `None`.
  The error now quotes the documented `YYYY-MM-DD` form rather than a
  strftime pattern, and shows the offending value with `repr`.

- Passing a `datetime` where a date filter documents accepting a `date` no
  longer raises `TypeError` from the FY2008 floor check. `time_period()`,
  `since()` and `until()` narrow a datetime to its date portion; the wire
  payload was never affected.

- A `TransactionsSearch` with no award set raises `ValidationError` from
  `count()` instead of requesting `/awards/count/transaction/None/`.

- `Award._load_agency_data` raises `ValidationError` rather than a bare
  `ValueError` for an invalid `agency_type`; `ValidationError` subclasses
  `ValueError`, so existing handlers are unaffected.

### Removed

- The internal `usaspending.utils.formatter` module, split into
  `usaspending.utils.dates`, `usaspending.utils.numbers` and
  `usaspending.utils.textcase`. Every symbol it held was absent from
  `__all__` and the README, so there is no compatibility shim. Only
  `current_fiscal_year` gets a documented new home, in `usaspending.utils`,
  as noted under Added.

- `Agency.__init__`'s third parameter, `subtier_data`. It was stored and
  never read; drop the argument, and use `Award.funding_subtier_agency` or
  `Award.awarding_subtier_agency` to reach subtier data.

- Module-level `usaspending.logging_config.get_logger`; the classmethod
  `USASpendingLogger.get_logger` is the one entry point.

- `AgencyAwardSummary.find_by_id`, which only ever raised
  `NotImplementedError` pointing at `get_awards_summary()`. The class is no
  longer a `SingleResourceBase`; that base class remains, unchanged, under
  the query classes that use it.

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
