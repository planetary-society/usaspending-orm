# claude.md

## Project Overview

USASpending Python Wrapper is a Python client library for the USAspending.gov API, providing a modern, client-centric interface with query builders, automatic pagination, and a plugin system for agency-specific functionality.

## Venv access
To access the virtual environment, run:
```bash
source .venv/bin/activate
```

## USASpending API Reference Documentation
See `api-docs-links.md` for official endpoint documentation links

## Architecture Principles

### Agency-agnostic implementation
- Designed to work with any agency's data
- No hardcoded agency logic
- Uses agency codes for filtering loaded via plugins
- Defaults to NASA as the primary agency for NASA-specific features

### Client-Centric Design
- All operations flow through a central `USASpending` client instance
- Resources accessed as properties: `client.awards`, `client.recipients`
- No global state or session variables
- Thread-safe through instance-based design

### Query Builder Pattern
- Chainable, immutable query construction via `_clone()` method
- Lazy evaluation - queries execute only when iterated
- Automatic, transparent pagination in `__iter__`
- Type-safe with Generic[T] base class

### Resource Organization
- Resources grouped in `resources/` directory
- Each resource inherits from `BaseResource`
- Resources create and return appropriate query builders
- Clean separation between resources and queries

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
├── plugins/              # Plugin system
└── utils/                # Utilities (retry, rate limit)
```

## Testing Strategy

### Test Organization
```
tests/
├── conftest.py           # Shared fixtures
├── test_client.py        # Client tests
├── queries/         # Query builder tests
├── models/          # Model tests
├── resources/       # Resource tests
└── fixtures/             # Test response data
```

### Testing Principles
- Use pytest for all tests
- Use fixture data from `tests/fixtures/` as much as possible
- Mock external API calls with `MockUSASpendingClient`
- Use `ResponseBuilder` for consistent response formatting

### Key Testing Patterns

#### Mock Client Setup
```python
@pytest.fixture
def mock_client():
    config = Config(
        cache_backend="memory",
        rate_limit_calls=1000,
    )
    client = USASpending(config)
    client._make_request = Mock()
    return client
```

#### Testing Query Builders
- Verify immutability with `_clone()`
- Test filter accumulation
- Verify pagination behavior
- Test `first()`, `all()`, `count()` methods

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

### Plugin System
- Simple registration via `client.register_plugin()`
- Initially data-only (e.g., agency codes)
- Plugins retrieved in query builders
- `AgencyPlugin` for agency name → code mapping

### Cache Abstraction
- Abstract `CacheBackend` interface
- File-based implementation with cachier
- Cache key generation from URL + params
- Only cache GET requests

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
- [ ] Tests cover pagination
- [ ] No hardcoded URLs/values
- [ ] Proper exception handling

## Common Implementation Tasks

### Adding a New Resource
1. Create `resources/new_resource.py`
2. Add property to `client.py`
3. Create corresponding query builder
4. Write comprehensive tests

### Adding Query Filter Methods
```python
def new_filter(self, value: str) -> "AwardSearch":
    """Add new filter with cloning."""
    clone = self._clone()
    clone._filters["new_key"] = value
    return clone
```

### Implementing Model Classes
- Use composition for nested data
- Lazy-load related models
- Store raw data in `_data`
- Provide property accessors

## Performance Considerations

### Rate Limiting
- Implement in `RateLimiter` class
- Configurable calls/period
- Block in `_make_request`
- No rate limiting in tests

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

### Public API Documentation
- All public methods documented
- Examples in docstrings
- Type hints complete
- Exceptions documented

## Security Considerations

### Input Validation
- Validate in query builders
- Sanitize before API calls
- Type checking via hints
- Clear error messages

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