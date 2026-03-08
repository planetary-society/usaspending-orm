# claude.md

## Project Overview

USASpending ORM is a Python ORM library for the USAspending.gov API, providing a modern, client-centric interface with query builders and automatic pagination.

## USASpending API Reference Documentation

- See `api-docs-links.md` for official endpoint documentation links
- Use `context7 MCP` to access the API documentation for the USASpending project and for any external libraries referenced in this codebase

## Architecture Principles

### Agency-agnostic implementation

- Designed to work with any agency's data
- No hardcoded agency logic
- Provides generic filters and helper methods

### Client-Centric Design

- All operations flow through a central `USASpendingClient` client
- Resources accessed as properties: `client.awards`, `client.recipients`, etc.
- No global state or session variables
- Thread-safe through instance-based design

### Query Builder Pattern

- Inspired by ActiveRecord and Django ORM syntax
- Chainable, immutable query construction via `_clone()` method
- Lazy evaluation - queries execute only when iterated
- Standard python List-like interface for results will fire relevant API calls (e.g. `len(client.awards)` fires off an API call to a `count` endpoint, for example)

### Resource Organization

- Resources grouped in `resources/` directory
- Each resource inherits from `BaseResource`
- Resources create and return appropriate query builders
- Clean separation between resources and queries

### Models and Data Structures

- Inspired by ActiveRecord and Django ORM structure
- Data models in `models/` directory
- Use composition for nested structures
- Raw API data stored in internal `_data` attribute and exposed via `raw()` method in `BaseModel`
- Properties provide access to structured data
- Properties use the `_lazy_get()` method to fetch data lazily for models inheriting from `LazyRecord`
- Models can chain their associations as QueryBuilder objects for one-to-many associations (e.g. `award.recipient.location.city`
- Models load related one-to-one associations as related model objects (e.g. `award.recipient`)
- Models provide a consistent API to underlying property names given the API's sometimes inconsistent naming conventions

## Code Style and Standards

### Python Guidelines

- Follow PEP 8 guidelines
- Follow code style in the linting settings in `pyproject.toml`
- FOLLOW BEST PRACTICES OBJECT-ORIENTED DESIGN
  - DON'T REPEAT YOURSELF (DRY)
  - Single Responsibility Principle
  - Don't over-engineer: keep it simple, stupid (KISS)

### Type Hints

- Use `from __future__ import annotations` for forward references
- Add type hints to ALL function signatures
- Use `TypeVar` and `Generic` for query builders
- Prefer `Optional[T]` over `Union[T, None]`

### Project Structure

```
src/usaspending/
├── client.py              # Main USASpendingClient
├── cli/                   # CLI tools (e.g., download_award)
├── config.py              # Configuration settings
├── download/              # Download job management
├── logging_config.py      # Custom logger configuration
├── exceptions.py          # Custom exceptions
├── resources/            # Resource classes
├── queries/              # Query builders
├── models/               # Data models
└── utils/                # Utilities (retry, rate limit)
```

## Testing Strategy

### Test Organization

```
tests/
├── conftest.py           # Shared fixtures
├── test_client.py        # Client tests
├── queries/              # Query builder tests
├── models/               # Model tests
├── resources/            # Resource tests
├── utils/                # Utility tests
├── mocks/                # Mock client and response builders
└── fixtures/             # Real-world POST-header and response JSON data from USASpending API
```

### Testing Principles

- Use `pytest` for test framework and implement pytest best practices
- Always integrate fixture data from `tests/fixtures/` into tests
- Aim for >80% test coverage
- Mock API client using the `mock_usa_client()` method and other helps in `tests/mocks/`
- Use helper methods to load fixtures and the mock client object in `tests/conftest.py`

## Quick Commands

- Run tests: `uv run pytest`
- Run integration tests: `uv run pytest -m integration`
- Lint: `uv run ruff check src/ tests/`
- Format: `uv run ruff format src/ tests/`
- No Justfile in this project

## Implementation Patterns

### Configuration

- Uses a global `config` object
- No environment variables in library code

### Resource Classes

- Lazy-loaded via property descriptors
- Stored in `_resources` dict
- Return query builder instances
- Handle resource-specific logic

### Query Builders

- Hierarchy: `BaseQuery[T]` -> `QueryBuilder[T]` -> `SearchQueryBuilder[T]`; also `ClientSideQueryBuilder[T]` (extends `BaseQuery`)
- `QueryBuilder[T]` handles paginated API queries; `ClientSideQueryBuilder[T]` handles client-side filtering
- Implement abstract methods:
  - `_endpoint()`: API endpoint
  - `_build_payload()`: Request payload
  - `_transform_result()`: Result transformation
  - `_clone()`: Return cloned instance
  - `__iter__()`: Iterable interface
- All filter methods return cloned instances

### Caching

- Implemented using `cachier` python library via `cachier` decorator
- Supports file (default, via pickle) and memory backends
- Dynamically reconfigurable at runtime via observer pattern (`register_cache_settings_observer` in `config.py`); cachier decorator is rebuilt when settings change
- Client uses cache-with-fallback: tries cached response first, falls back to uncached on failure
- Cache configurable via the global `config` object set in `src/usaspending/config.py`:
  - `cache_enabled`: Enable/disable caching (default: False)
  - `cache_ttl`: `timedelta` TTL (default: 1 week); `configure()` accepts seconds as `int`/`float`
  - `cache_timeout`: Seconds to wait for cache entry processing (default: 60)
  - `cache_dir`: Directory for file-based cache (default: "~/.cache/usaspending")
  - `cache_backend`: Backend type ('file' or 'memory', default: 'file')
  - `cache_namespace`: Namespace for cache keys (default: 'usaspending-orm')

### Logging

- Implemented via custom `USASpendingLogger` class using Python's `logging` module
- Log all API requests and responses, including total counts of API calls
- Log query execution times
- Implement variable log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)

## Development Workflow

### Adding New Features

1. Define interface in resource class
2. Create query builder if needed
3. Write tests first (TDD)
4. Implement with full type hints
5. Add to `__all__` exports
6. Document in docstrings

### Code Review Checklist

- [ ] All methods have type hints
- [ ] Docstrings follow Google style
- [ ] Proper exception handling
- [ ] PEP 8 pythonic code style
- [ ] Code is DRY, object-oriented, clear and maintainable
- [ ] Passes `ruff` linting and formatting check

## Error Handling

### Exception Hierarchy

- `USASpendingError` - Base exception
- `APIError` - API response errors
- `HTTPError` - Network/transport layer errors (retryable 5xx)
- `RateLimitError` - Rate limit exceeded
- `ValidationError` - Invalid parameters
- `DetachedInstanceError` - Lazy-loading on closed/detached client
- `ConfigurationError` - Invalid configuration settings
- `DownloadError` - File download/extraction failures

### Retry Logic

- Implemented in `RetryHandler`
- Exponential backoff
- Configurable max attempts
- Only retry on specific errors

## Documentation Standards

### Docstring Requirements

- Google style format
- Include parameter types
- Document return values
- Add usage examples
- Note any side effects

## Release Process

### Quality Gates

- 100% public API documented
- Type hints pass mypy
- Tests pass with >80% coverage
- No TODO/FIXME in code

### Versioning Strategy

- Semantic versioning
- Alpha releases initially
- Document all changes
- Migration guides for major versions

## Special Instructions

- **Use full agency names and not acronyms in examples and docstrings. For example always use `National Aeronautics and Space Administration` instead of `NASA` when referencing the space agency.**
- **This file is committed to the repository and so should never include any secrets.**
- **Always read `README.md` before making changes.**
- **Cross-reference:** Also read `api-docs-links.md` for detailed contributor guidelines.
- **When adding new features, update all relevant docs, tests, and requirements files.**
- **All code must be Python 3.9+ compatible.**
- **When in doubt, prefer explicit, readable code over cleverness.**
- **Never use non-ASCII characters or the em dash.**
- **When referencing/calling external libraries, use `context7 MCP` to get latest documentation.**
- **All new code must have full type annotations and Google-style docstrings.**
