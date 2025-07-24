# claude.md

## Project Overview

USASpending Python Wrapper is a Python client library for the USAspending.gov API, providing a modern, client-centric interface with query builders and automatic pagination.

## USASpending API Reference Documentation
See `api-docs-links.md` for official endpoint documentation links
You may also use contex7 MCP to access the API documentation for the `usaspendingapi` project.

## Architecture Principles

### Agency-agnostic implementation
- Designed to work with any agency's data
- No hardcoded agency logic
- Provides generic filters and helper methods

### Client-Centric Design
- All operations flow through a central `USASpending` client instance
- Resources accessed as properties: `client.awards`, `client.recipients`, etc.
- No global state or session variables
- Thread-safe through instance-based design

### Query Builder Pattern
- Chainable, immutable query construction via `_clone()` method
- Lazy evaluation - queries execute only when iterated
- Automatic, transparent pagination in `__iter__`
- Standard python List-like interface for results will fire relevant API calls (e.g. `len(client.awards)` fires off an API call to a `count` endpoint, for example)
- Type-safe with Generic[T] base class

### Resource Organization
- Resources grouped in `resources/` directory
- Each resource inherits from `BaseResource`
- Resources create and return appropriate query builders
- Clean separation between resources and queries

### Models and Data Structures
- Data models in `models/` directory
- Use composition for nested structures
- Raw API data stored in `_data` attribute
- Properties provide access to structured data
- Models are lazy-loaded to avoid unnecessary API calls and to ensure access to full data set
- Models can chain their associations (e.g. `award.transactions` to get all transactions for an award)
- Models provide helper methods to provide consitent naming conventions and data access patterns

## Code Style and Standards

### Python Guidelines
- Follow PEP 8 strictly
- Target Python 3.8+ for broad compatibility
- Use descriptive variable names
- Keep functions focused and single-purpose
- Prefer composition over inheritance

### Type Hints
- Use `from __future__ import annotations` for forward references
- Add type hints to ALL function signatures
- Use `TypeVar` and `Generic` for query builders
- Prefer `Optional[T]` over `Union[T, None]`

### Project Structure
```
src/usaspendingapi/
├── client.py              # Main USASpending client
├── config.py              # Configuration dataclass
├── exceptions.py          # Custom exceptions
├── resources/            # Resource classes
├── queries/              # Query builders
├── models/               # Data models
├── cache/                # Cache backends
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
- Use pytest for test framework
- Use fixtures in `tests/fixtures/` for common test data
- Use TDD (Test-Driven Development) approach
- Aim for >80% test coverage
- Use helper methods in `tests/mocks/` for mocking external API calls and resources

## Implementation Patterns

### Configuration
- Single `Config` dataclass with sensible defaults
- No environment variables in library code
- Configuration passed at client instantiation

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
- All filter methods return cloned instances

### Pagination Strategy
- Automatic in `__iter__` method
- Check `hasNext` in response metadata
- Support `max_pages` limit
- Page size limited to API maximum (100)
- Must be responsive to user-provided limit() filters (i.e. should not load more results than the user requested)

### Caching
- Implemented using `cachier` library for flexible backend support
- Supports file (default), memory, MongoDB, Redis, and SQL backends
- Cache configurable via `Config` dataclass:
  - `cache_enabled`: Enable/disable caching (default: True)
  - `cache_ttl`: Time-to-live in seconds (default: 604800 = 1 week)
  - `cache_dir`: Directory for file-based cache (default: ".usaspending_cache")
- Only caches GET requests (POST requests are never cached)
- Supports cachier's per-call options (skip_cache, overwrite_cache, etc.)

### Logging
- Implementd via custom `Logger` class using Python's `logging` module
- Log all API requests and responses, including total counts of API calls
- Log query execution times
- Config DEBUG or INFO level in `Config` dataclass

## Development Workflow

### Adding New Features
1. Define interface in resource class
2. Create query builder if needed
3. Write tests first (TDD)
4. Implement with full type hints
5. Add to `__all__` exports
6. Document in docstrings

### Code Review Checklist
- [ ] Query builders use `_clone()`
- [ ] All methods have type hints
- [ ] Docstrings follow Google style
- [ ] Proper exception handling
- [ ] Pythonic code style
- [ ] Simplicity and clarity are paramount

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