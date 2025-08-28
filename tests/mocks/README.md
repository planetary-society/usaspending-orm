# Mock Client Documentation

This directory contains the new universal mock client for USASpending API tests.

## Overview

The `MockUSASpendingClient` provides a comprehensive mocking system that makes it easier to write tests for the USASpending API wrapper. It replaces the old pattern of manually mocking `_make_request` with a more intuitive interface.

## Key Features

- **Automatic Pagination**: Easily set up paginated responses without manually managing page sequences
- **Fixture Loading**: Load responses directly from JSON fixture files
- **Error Simulation**: Simulate API errors with proper exception handling
- **Request Tracking**: Track and assert on requests made during tests
- **Rate Limiting**: Optional rate limiting simulation for performance tests
- **Response Sequencing**: Return different responses for subsequent calls to the same endpoint

## Migration Guide

### Old Pattern (Manual Mock)

```python
@pytest.fixture
def mock_client():
    config = Config(cache_backend="memory", rate_limit_calls=1000)
    client = USASpending(config)
    client._make_request = Mock()
    return client

def test_award_search(mock_client):
    # Manual mock setup
    mock_client._make_request.side_effect = [
        {
            "results": [{"Award ID": "1"}, {"Award ID": "2"}],
            "page_metadata": {"hasNext": True}
        },
        {
            "results": [{"Award ID": "3"}],
            "page_metadata": {"hasNext": False}
        }
    ]
    
    # Test execution
    results = list(mock_client.awards.search().with_award_types("A"))
    assert len(results) == 3
    
    # Manual assertion
    assert mock_client._make_request.call_count == 2
```

### New Pattern (MockUSASpendingClient)

```python
def test_award_search(mock_usa_client):
    # Simple mock setup
    mock_usa_client.mock_award_search([
        {"Award ID": "1"},
        {"Award ID": "2"}, 
        {"Award ID": "3"}
    ])
    
    # Test execution
    results = list(mock_usa_client.awards.search().with_award_types("A"))
    assert len(results) == 3
    
    # Built-in assertion
    assert mock_usa_client.get_request_count() == 1  # Auto-paginated
```

## Usage Examples

### Basic Award Search

```python
def test_award_search(mock_usa_client):
    mock_usa_client.mock_award_search([
        {"Award ID": "123", "Recipient Name": "SpaceX", "Award Amount": 1000000},
        {"Award ID": "456", "Recipient Name": "Blue Origin", "Award Amount": 2000000}
    ])
    
    results = list(
        mock_usa_client.awards.search()
        .with_award_types("A")
        .with_keywords("space")
    )
    
    assert len(results) == 2
    assert results[0]._data["Recipient Name"] == "SpaceX"
```

### Pagination Testing

```python
def test_pagination(mock_usa_client):
    # Create 250 awards, auto-paginated at 100 per page
    awards = [{"Award ID": f"AWD-{i}"} for i in range(250)]
    mock_usa_client.set_paginated_response(
        "/v2/search/spending_by_award/",
        awards,
        page_size=100
    )
    
    results = list(mock_usa_client.awards.search().with_award_types("A"))
    
    assert len(results) == 250
    assert mock_usa_client.get_request_count("/v2/search/spending_by_award/") == 3
```

### Error Simulation

```python
def test_api_error(mock_usa_client):
    mock_usa_client.set_error_response(
        "/v2/search/spending_by_award/",
        error_code=400,
        detail="Invalid award type: X"
    )
    
    with pytest.raises(APIError) as exc_info:
        list(mock_usa_client.awards.search().with_award_types("X"))
    
    assert exc_info.value.status_code == 400
    assert "Invalid award type" in str(exc_info.value)
```

### Fixture Loading

```python
def test_with_fixture(mock_usa_client):
    # Load from tests/fixtures/awards
    mock_usa_client.set_fixture_response(
        "/v2/awards/CONT_AWD_123/",
        "award"
    )
    
    award = mock_usa_client.awards.find_by_generated_id("CONT_AWD_123")
    assert award.recipient.name == "The University of Iowa"  # From fixture
```

### Request Tracking

```python
def test_request_tracking(mock_usa_client):
    mock_usa_client.mock_award_search([])
    
    list(
        mock_usa_client.awards.search()
        .with_award_types("A")
        .with_keywords("space")
    )
    
    # Check what was sent
    last_request = mock_usa_client.get_last_request()
    payload = last_request["json"]
    
    assert payload["filters"]["award_type_codes"] == ["A"]
    assert payload["filters"]["keywords"] == ["space"]
    
    # Or use assertion helper
    mock_usa_client.assert_called_with(
        "/v2/search/spending_by_award/",
        method="POST"
    )
```

### Count Testing

```python
def test_award_counts(mock_usa_client):
    mock_usa_client.mock_award_count(
        contracts=150,
        grants=300,
        loans=25
    )
    
    assert mock_usa_client.awards.search().contracts().count() == 150
    assert mock_usa_client.awards.search().grants().count() == 300
    assert mock_usa_client.awards.search().loans().count() == 25
```

## Available Methods

### MockUSASpendingClient

- `set_response(endpoint, response_data, status_code=200)`: Set single response
- `set_paginated_response(endpoint, items, page_size=100)`: Auto-paginate items
- `set_fixture_response(endpoint, fixture_name)`: Load from fixture file
- `set_error_response(endpoint, error_code, error_message, detail)`: Simulate errors
- `add_response_sequence(endpoint, responses)`: Multiple responses in sequence
- `mock_award_search(awards, page_size=100)`: Convenience for award search
- `mock_award_count(**counts)`: Convenience for award counts
- `mock_award_detail(award_id, **data)`: Convenience for award detail
- `get_request_count(endpoint=None)`: Get number of requests made
- `get_last_request(endpoint=None)`: Get last request data
- `assert_called_with(endpoint, method, json, params)`: Assert specific request
- `reset()`: Clear all mock state

### ResponseBuilder

- `paginated_response(results, page, has_next, total)`: Build paginated response
- `award_search_response(awards, page, has_next)`: Build award search response
- `count_response(**counts)`: Build count response
- `error_response(status_code, detail, error)`: Build error response
- `award_detail_response(award_id, **data)`: Build award detail response

## Best Practices

1. **Use convenience methods**: `mock_award_search()`, `mock_award_count()`, etc.
2. **Test realistic scenarios**: Use data that looks like real API responses
3. **Test error conditions**: Use `set_error_response()` to test error handling
4. **Assert on requests**: Use `assert_called_with()` to verify correct API calls
5. **Reset between tests**: Call `reset()` or use fresh fixture instances
6. **Use fixtures**: Load real API responses from fixture files when possible

## Testing the Mock Client

The mock client itself is tested in `test_mock_client.py`. Run with:

```bash
python -m pytest tests/mocks/test_mock_client.py -v
```

Example usage tests are in `test_mock_client_example.py`:

```bash
python -m pytest tests/test_mock_client_example.py -v
```

## Files in this Directory

- `__init__.py`: Package initialization with exports
- `mock_client.py`: Main `MockUSASpendingClient` class
- `response_builder.py`: Helper class for building API responses
- `test_mock_client.py`: Tests for the mock client implementation
- `migration_example.py`: Side-by-side comparison of old vs new patterns
- `README.md`: This documentation file

## Quick Start

1. Use the `mock_usa_client` fixture in your tests:
   ```python
   def test_my_feature(mock_usa_client):
       # Your test here
   ```

2. Set up simple responses:
   ```python
   mock_usa_client.mock_award_search([
       {"Award ID": "123", "Recipient Name": "Test Corp"}
   ])
   ```

3. Execute your test logic:
   ```python
   results = list(mock_usa_client.awards.search().with_award_types("A"))
   assert len(results) == 1
   ```

4. Make assertions:
   ```python
   assert mock_usa_client.get_request_count() == 1
   ```

That's it! The mock client handles pagination, error simulation, and request tracking automatically.