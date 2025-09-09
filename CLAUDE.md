# claude.md

## Project Overview

USASpending ORM is a Python ORM library for the USAspending.gov API, providing a modern, client-centric interface with query builders and automatic pagination.

## USASpending API Reference Documentation
- See `api-docs-links.md` for official endpoint documentation links
- Use **contex7 MCP** to access the API documentation for the USASpending project.

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
- Models are lazy-loaded to avoid unnecessary API calls and to ensure access to full data set
- Properties use the `_lazy_get()` method to fetch data lazily for models inheriting from `LazyRecord`
- Models can chain their associations as QueryBuilder objects for one-to-many associations (e.g. `award.transactions.all()`
- Models load related one-to-one associations as related model objects (e.g. `award.recipient`)
- Models provide a consistent API to underlying property names given the API's sometimes inconsistent naming conventions

## Code Style and Standards

### Python Guidelines
- Follow PEP 8 strictly
- Prefer simple, readable code
- Don't over-engineer solutions! Implement the simplest solution that works
  unless specifically required otherwise
- Target Python 3.9+ for broad compatibility
- Use descriptive variable names
- Keep functions focused and single-purpose
- Use ruff to check linting and formatting

### Type Hints
- Use `from __future__ import annotations` for forward references
- Add type hints to ALL function signatures
- Use `TypeVar` and `Generic` for query builders
- Prefer `Optional[T]` over `Union[T, None]`

### Project Structure
```
src/usaspending/
├── client.py              # Main USASpendingClient
├── config.py              # Configuration settings
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
└── fixtures/             # Real-world POST-header and response JSON data from USASPending API
```

### Testing Principles
- Use pytest for test framework and implement pytest best practices
- Use fixtures in `tests/fixtures/` for common test data
- Use TDD (Test-Driven Development) approach
- Aim for >80% test coverage
- Mock API client using the `mock_usa_client()` method and other helps in `tests/mocks/`
- Use helper methods to load fixtures and the mock client object in `tests/conftest.py`


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
- Inherit from `QueryBuilder[T]` base
- Implement abstract methods:
  - `_endpoint()`: API endpoint
  - `_build_payload()`: Request payload
  - `_transform_result()`: Result transformation
  - `_clone()`: Return cloned instance
  - `__iter__()`: Iterable interface
- All filter methods return cloned instances

### Caching
- Implemented using `cachier` python library via `cachier` decorator
- Supports file (default, via pickle) and memory backendds
- Cache configurable via the global `config` object set in `src/usaspending/config.py`:
  - `cache_enabled`: Enable/disable caching (default: True)
  - `cache_ttl`: Time-to-live in seconds (default: 604800 = 1 week)
  - `cache_dir`: Directory for file-based cache (default: ".usaspending_cache")
  - `cache_backend`: Backend type ('file' or 'memory', default: 'file')

### Logging
- Implementd via custom `USASpendingLogger` class using Python's `logging` module
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
- [ ] Pythonic code style
- [ ] Simplicity and clarity are paramount
- [ ] Passes `ruff` linting and formatting check

## Error Handling

### Exception Hierarchy
- `USASpendingError` - Base exception
- `APIError` - API response errors
- `RateLimitError` - Rate limit exceeded
- `ValidationError` - Invalid parameters

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

## 🧠 Claude Code: Special Instructions

- **This file is committed to the repository and so should never include any secrets.**
- **Always read this file, `README.md` before making changes.**
- **Cross-reference:** Also read `api-docs-links.md` for detailed contributor guidelines.
- **When adding new features, update all relevant docs, tests, and requirements files.**
- **All code must be Python 3.9+ compatible.**
- **If you are stuck, suggest opening a new chat with the latest context.**
- **When in doubt, prefer explicit, readable code over cleverness.**
- **Never use non-ASCII characters or the em dash.**
- **If adding new dependencies, use context7 MCP to get latest versions.**
- **Use per-file or per-line ignores for ruff only when justified.**
- **All new code must have full type annotations and Google-style docstrings.**