# USASpending ORM

A python library that provides an object-relational mapping layer to the USAspending.gov API.

## Why This Library?

[USASpending.gov](https://usaspending.gov) is the official federal database for tracking U.S. government spending, and provides extensive data on federal contracts, grants, and other awards since 2007-10-01, enabling citizens to track how federal money is spent.

The platform has a [comprehensive API](https://api.usaspending.gov) for querying the data, but the API is complex and can be cumbersome to work with. This library provides an abstraction layer and other quality-of-life improvements to enable rapid development of applications that consume USASpending data.

## Key Features

**🔗 ORM-Style Chained Interface** - Access related data through object associations (e.g., `award.recipient.location.city`) inspired by ActiveRecord and SQLAlchemy. Navigate related data without manual API calls.

**🔎 Comprehensive Award Queries** - Build complex searches with chainable filters for agencies, award types, fiscal years, and more. 

**⚡️ Smart Caching & Rate Limiting** - Optional file-based caching to dramatically improve performance for repeated queries. Automatic rate limiting and retry logic handles API throttle limits during bulk operations.

**🛡️ Data Normalization and Type Casting** - Consistent field naming across resources, with lazy-loading for nested data and automatic type conversion.

**🥩 Raw API Output Preserved** - Access the original API JSON response via the `.raw` property on any resource object when you need the underlying data structure.

## Installation

```bash
pip install usaspending-orm
```

Requires Python 3.9 or higher. No API key required.

## Usage

The library provides a `USASpendingClient` class that manages the connection to the USASpending API and provides access to various resources such as awards, recipients, agencies, etc. This can be used as a context manager to ensure proper session management
or can be instantiated directly.

#### Load the client
```python
from usaspending import USASpendingClient
```

#### Then load a specific award by its Award ID
```python
with USASpendingClient() as client:
    award = client.awards.find_by_award_id("80GSFC18C0008")
```

#### Access related Award properties via chained object associations
```python
with USASpendingClient() as client:
    award = client.awards.find_by_award_id("80GSFC18C0008")
    award.recipient.location.full_address # -> 105 Jessup Hall, Iowa City, IA, 52242, United States
    award.subawards.count() # -> 100
    award.subawards[2].recipient.place_of_performance.district # -> AL-03
```

#### Searching for Awards

You can query awards data using the `search()` method on the `client.awards` object:

```python

with USASpendingClient() as client:
    awards_query = client.awards.search()
```

Search parameters are outlined in the [spending_by_award](https://github.com/fedspendingtransparency/usaspending-api/raw/refs/heads/master/usaspending_api/api_contracts/contracts/v2/search/spending_by_award.md) endpoint of the USASpending API. Every search parameter is applied via a matching "snake_case" method name. These methods can be chained together to build complex queries.

``` python
awards_query = client.awards.search() \
    .agencies({"name":"National Aeronautics and Space Administration", "type":"awarding", "tier":"toptier"}) \  
    .grants() \
    .keywords("Perseverance","Mars")
```

This returns a query object that can be further refined or executed to return results.
The methods `.all()`, `.first()`, `.count()` will trigger a query to the API, as will iterating over the query object.

### Example: Searching for NASA Contracts to SpaceX in 2023

```python

with USASpendingClient() as client:
    
    # Create query object with chained filters
    awards_query = client.awards.search() \
        .agency("National Aeronautics and Space Administration") \
        .recipient_search_text("Space Exploration Technologies") \
        .contracts() \
        .fiscal_year(2023) \
        .order_by("Award Amount", "desc")
    
    # -> <AwardQuery ...> object, no API call made yet
    
    # Return results count without fetching all records
    count = awards_query.count() # -> 8

    # Fetch first result (query executes here)
    top_spacex_award = awards_query.first()
    
    # Returned value is an Award object with all properties mapped
    # and properly typed. 
    top_spacex_award.total_obligation  # -> Decimal('3029850123.69')
    top_spacex_award.category  # -> "contract"
    top_spacex_award.description  # -> "The Commercial Crew Program (CCP) contract ...."
    
    # Helper methods provide easy access to common fields without having to account for
    # inconsistent naming or nested structures in the raw API response
    top_spacex_award.award_identifier  # -> "80GSFC18C0008"
    top_spacex_award.start_date  # -> datetime.date(2016, 12, 30)
    top_spacex_award.end_date  # -> datetime.date(2023,12,31)

    # The resulting object provides a normalized interface to the full Award record,
    # and provides access to related data via chained associations
    
    # Recipient information
    top_spacex_award.recipient.name  # -> "Space Exploration Technologies Corp."
    top_spacex_award.recipient.location.city  # -> "Hawthorne"

    # Award Transactions
    last_transaction = top_spacex_award.transactions.order_by("action_date", "desc").first()
    last_transaction.action_date  # -> datetime.date(2025, 10, 08)
    last_transaction.action_type_description  # -> "SUPPLEMENTAL AGREEMENT FOR WORK WITHIN SCOPE"

```

## Configuration

### Session Management and Lazy-Loading

The library uses lazy-loading to avoid unnecessary API calls. Missing award and Recipient properties will trigger an API call to fetch the missing data. This means models require an active client session to load missing data on demand.

#### Session Lifecycle

Use the client as a context manager (recommended) or explicitly call `close()`:

```python
# Pattern 1: Access all data within the context (recommended)
with USASpendingClient() as client:
    awards = client.awards.search().agencies("NASA").all()
    for award in awards:
        # Access lazy-loaded properties inside the context
        print(f"{award.recipient_name}: ${award.total_obligation:,.2f}")
        print(f"Subawards: {award.subaward_count}")
# Session automatically closed here
```

Accessing related properties after the client session closes raises a `DetachedInstanceError`:

```python
# This will raise DetachedInstanceError
with USASpendingClient() as client:
    awards = client.awards.search().all()
# Client is closed here

# This will raise DetachedInstanceError
print(awards[0].transactions.count())
```

You can also reattach objects to a new session if needed:

```python
# Create objects in one session
with USASpendingClient() as client:
    award = client.awards.find_by_award_id("80GSFC18C0008")

# Reattach to a new session to access related properties
with USASpendingClient() as new_client:
    award.reattach(new_client)
    print(f"Subawards: {award.subawards.count()}")  # Works!

    # Recursive reattach for nested objects
    award.reattach(new_client, recursive=True)
    print(f"Recipient: {award.recipient.name}")  # Recipient also reattached
```

### Performance & Caching

By default, caching is **disabled**. However, enabling caching can dramatically improve performance and reduce API load for repeated queries, especially during development or when working with large datasets.

To enable caching, load the configuration module and set `cache_enabled=True` before creating a client instance:

```python
from usaspending import config as usaspending_config, USASpendingClient

# Enable with defaults (1 week TTL, file-based storage)
usaspending_config.configure(cache_enabled=True)

with USASpendingClient() as client:
    # All queries will now be cached
    awards = client.awards.search().agencies("NASA").all()
```

The library defaults to file-based caching with a 1-week TTL, but you can customize these settings as needed:

```python
usaspending_config.configure(
    cache_enabled=True,           # Enable caching
    cache_ttl=86400,              # Cache for 1 day (default: 1 week)
    cache_backend="memory",         # "file" or "memory" (default: "file")
)
```

**File-based caching** (default):
- Persists between Python sessions
- Stored in `~/.cache/usaspending` directory
- Uses pickle for serialization
- Best for production and development workflows

**Memory-based caching**:
- Faster access, no disk I/O
- Cleared when Python process ends
- Best for single-session data exploration
- Enable with `cache_backend="memory"`

### Customizable Settings

The library applies some sensible defaults that work for most use cases:

- Rate limiting: 1000 calls per 5 minutes (respecting USASpending API limits)
- Caching: disabled by default (see Performance & Caching section above to enable)

Customize these settings before creating a client instance if needed:

```python
from usaspending import config as usaspending_config

# Configure settings before creating the client
usaspending_config.configure(
    # Cache settings (caching is disabled by default)
    cache_enabled=True,           # Enable caching
    # Set file-cache directory (default: ~/.usaspending_cache)
    cache_dir="/tmp/usaspending_cache",
    # Set cache expiration time (default 1 week)
    cache_ttl=86400,
    # Set cache backend to be in-memory "memory" or "file" for file-based caching via pickle (default: "file")
    cache_backend="memory",

    # Set rate limiting parameters
    # Set number of calls allowed within the rate limit period (default: 1000)
    rate_limit_calls=500,
    # Rate limit period (in seconds, default: 300)
    rate_limit_period=60,

    # Set HTTP request parameters (default: max_retries=3, timeout=30)
    # Set number of retries for failed requests (default: 3)
    max_retries=5,
    # Set delay between retries in seconds (default: 1.0)
    retry_delay=10.0,
    # Set exponential backoff factor for retries (default: 2.0)
    retry_backoff=2.0,
    # Set request timeout in seconds (default: 30)
    timeout=60  # Longer timeout for slow connections (default: 30)
)

```

### Logging Configuration

The library provides detailed logging, which you can configure in your application:

```python
import logging
from usaspending import USASpendingClient

# Configure root logger (affects all loggers)
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

```

## Project Status

USASpending Python Wrapper is under active development. The API is stabilizing but may change as we refine the abstractions based on real-world usage. We welcome feedback on the interface design and feature priorities.

## Contributing

We welcome contributions to improve and expand the implementation and functionality.

## About The Planetary Society

This library was initially developed to serve the needs of The Planetary Society's Space Policy and Advocacy team in tracking and analyzing NASA contract data, and is in-use in our internal and external data tools.

We have open-sourced the project to enable others to better use USASpending data. 

[The Planetary Society](planetary.org) is an independent nonprofit organization that empowers the world's citizens to advance space science and exploration. The organization is supported by individuals across the world, and does not accept government grants nor does it have major aerospace donations.

Please consider supporting our work by [becoming a member](https://www.planetary.org/join).

## License

MIT License