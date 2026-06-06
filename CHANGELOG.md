# Changelog

All notable changes to the USASpending ORM library are documented here.
The format loosely follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and the project adheres to [Semantic Versioning](https://semver.org/).

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
