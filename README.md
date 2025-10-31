# USASpending ORM

A python library that provides an object-relational mapping layer to the USAspending.gov API, simplifying access to rich contract and procrement data of the U.S. government.

[USASpending.gov](https://usaspending.gov) is the official federal database for tracking U.S. government spending, established by Federal Funding Accountability and Transparency Act of 2006. The platform provides extensive data on federal contracts, grants, and other awards since 2007-10-01, enabling citizens to track how federal money is spent.

The platform provides access to a [comprehensive API](https://api.usaspending.gov) for querying the data, but the API is complex and can be cumbersome to work with. This library provides an abstraction layer that focuses on common use cases, offering a clean, Pythonic interface for accessing and processing the data.

## Why This Library?

**Without this library**, working with the USASpending API requires:
- Manually constructing complex JSON payloads for POST requests
- Implementing pagination logic to handle large result sets
- Managing rate limits and retry logic for failed requests
- Navigating inconsistent field naming across endpoints
- Writing boilerplate code for caching and session management

**With this library**, the same tasks become:
```python
with USASpendingClient() as client:
    
    # Create query object with chained filters
    # Find all NASA contracts to SpaceX in 2023, ordered by value
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



ate limiting, caching, and session management are handled automatically.

## Key Features

**🔗 ORM-Style Chained Interface** - Access related data through object associations using intuitive, ActiveRecord-inspired syntax (e.g., `award.recipient.location.city`). Navigate the data model without manual API calls.

**🔎 Comprehensive Award Queries** - Build complex searches with chainable filters for agencies, award types, fiscal years, and more. No need to construct raw API payloads or parse parameters.

**⚡️ Smart Caching & Rate Limiting** - Optional file-based caching can dramatically improve performance for repeated queries. Automatic rate limiting prevents hitting API throttle limits during bulk operations.

**📄 Transparent Pagination** - Iterate through thousands of records as if working with a standard Python list. Pagination is handled automatically behind the scenes.

**🛡️ Data Normalization and Type Casting** - Consistent field naming across resources, with lazy-loading for nested data and automatic type conversion. Missing fields handled gracefully.

**🥩 Raw API Output Available** - Access the original API JSON response via the `.raw` property on any resource object when you need the underlying data structure.

## Installation

```bash
pip install usaspending-orm
```

Requires Python 3.9 or higher. No API key required.

## Usage

### Load the client
```python
>>> from usaspending import USASpendingClient
```

### Load a specific award by its Award ID
```python
>>> with USASpendingClient() as client:
...     award = client.awards.find_by_award_id("80GSFC18C0008")
```

### Access properties and queries via chained object associations
```python
>>> with USASpendingClient() as client:
...     award = client.awards.find_by_award_id("80GSFC18C0008")
...     print(award.recipient.location.full_address)
...     print(f"Subawards: {award.subawards.count()}")
...     print(f"District: {award.subawards[2].recipient.place_of_performance.district}")
105 Jessup Hall
Iowa City, IA, 52242
United States
Subawards: 100
District: AL-03
```

### Search for awards with complex filters
```python
# Find NASA contracts in FY 2023, ordered by value
>>> with USASpendingClient() as client:
...     award_query = client.awards.search() \
...                 .agencies("National Aeronautics and Space Administration") \
...                 .contracts() \
...                 .fiscal_year(2023)
...
...     # Get total count without fetching all records
...     print(f"Total awards: {award_query.count()}")
...
...     # Sort by award amount descending
...     award_query = award_query.order_by("Award Amount", "desc")
...
...     # Query executes lazily when results are accessed
...     top_10 = award_query[:10]
...     for award in top_10:
...         print(f"{award.recipient_name}: ${award.total_obligation:,.0f}")
```

### Queries are iterable
```python
>>> with USASpendingClient() as client:
...     award_query = client.awards.search() \
...                 .agencies("National Aeronautics and Space Administration") \
...                 .contracts() \
...                 .fiscal_year(2022)
...
...     print(f"Query length: {len(award_query)}")
...
...     # Access specific award by index
...     award = award_query[5000]
...     for transaction in award.transactions[:3]:  # Show first 3 transactions
...         print(f"{transaction.action_date}: ${transaction.federal_action_obligation:,.2f}")
```

## Configuration

### Session Management and Lazy-Loading

The library uses lazy-loading to avoid unnecessary API calls. Model properties that require API requests are fetched only when accessed. This means models need an active client session to load data on demand.

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

# Pattern 2: Eager loading before context exits
with USASpendingClient() as client:
    awards = client.awards.search().limit(10).all()

    # Fetch all lazy data before exiting
    for award in awards:
        award.fetch_all_details()

        # Explicitly fetch related objects if needed
        if award.recipient:
            award.recipient.fetch_all_details()

        if award.awarding_agency:
            award.awarding_agency.fetch_all_details()

# Now safe to use awards and their related objects outside the context
print(f"Recipient: {awards[0].recipient.name}")
print(f"Agency: {awards[0].awarding_agency.name}")

# Pattern 3: Explicit cleanup when you need long-lived models
client = USASpendingClient()
try:
    awards = client.awards.search().agencies("NASA").all()
    # Use awards and access lazy properties...
    print(awards[0].subaward_count)  # Works because client is still open
finally:
    client.close()  # Close when actually done

# Pattern 4: Reattach objects to a new session
# Create objects in one session
with USASpendingClient() as client:
    award = client.awards.find_by_award_id("80GSFC18C0008")

# Reattach to a new session to access lazy properties
with USASpendingClient() as new_client:
    award.reattach(new_client)
    print(f"Subawards: {award.subaward_count}")  # Works!

    # Recursive reattach for nested objects
    award.reattach(new_client, recursive=True)
    print(f"Recipient: {award.recipient.name}")  # Recipient also reattached
```

#### Avoiding DetachedInstanceError

Accessing lazy-loaded properties after the client session closes raises a `DetachedInstanceError`:

```python
# This will raise DetachedInstanceError
with USASpendingClient() as client:
    awards = client.awards.search().all()
# Client is closed here

print(awards[0].subaward_count)  # Error! Session is closed

# Solution: Use one of the patterns above
```

### Performance & Caching

By default, caching is **disabled** to ensure you always receive fresh data from the USASpending API. However, for production use or when working with large datasets, enabling caching can dramatically improve performance and reduce API load.

#### Why Enable Caching?

- **Faster queries**: Cached responses return instantly instead of waiting for API calls
- **Reduced API load**: Fewer requests to USASpending.gov servers
- **Rate limit protection**: Avoid hitting API throttle limits during bulk operations
- **Cost savings**: Especially important when iterating on queries during development

#### Performance Comparison

```python
# Without caching (default)
with USASpendingClient() as client:
    awards = client.awards.search().agencies("NASA").fiscal_year(2023).all()
# First run: ~15-30 seconds for 5000+ records
# Second run: ~15-30 seconds (fresh API call every time)

# With caching enabled
from usaspending import config as usaspending_config
usaspending_config.configure(cache_enabled=True)

with USASpendingClient() as client:
    awards = client.awards.search().agencies("NASA").fiscal_year(2023).all()
# First run: ~15-30 seconds (populates cache)
# Second run: <1 second (served from cache)
```

#### Enabling Caching

Enable caching before creating your client:

```python
from usaspending import config as usaspending_config, USASpendingClient

# Enable with defaults (1 week TTL, file-based storage)
usaspending_config.configure(cache_enabled=True)

with USASpendingClient() as client:
    # All queries will now be cached
    awards = client.awards.search().agencies("NASA").all()
```

#### Caching Options

Customize caching behavior to fit your needs:

```python
usaspending_config.configure(
    cache_enabled=True,           # Enable caching
    cache_ttl=86400,              # Cache for 1 day (default: 1 week)
    cache_backend="file",         # "file" or "memory" (default: "file")
    cache_dir="~/.usaspending_cache"  # Cache directory (default)
)
```

**File-based caching** (default):
- Persists between Python sessions
- Stored in `~/.usaspending_cache` directory
- Uses pickle for serialization
- Best for production and development workflows

**Memory-based caching**:
- Faster access, no disk I/O
- Cleared when Python process ends
- Best for single-session data exploration
- Enable with `cache_backend="memory"`

#### Cache Management

```python
# View cache location
print(usaspending_config.cache_dir)

# Clear the cache manually (file-based only)
import shutil
shutil.rmtree(usaspending_config.cache_dir)

# Disable caching temporarily
usaspending_config.configure(cache_enabled=False)
```

#### When to Use Caching

**Enable caching when:**
- Running repeated queries during development
- Building dashboards or reports
- Processing large datasets in production
- Working with historical data that changes infrequently

**Disable caching when:**
- You need real-time, up-to-date data
- Working with actively changing datasets
- Testing or debugging API behavior
- Storage space is limited

### Customizable Settings

The library uses sensible defaults that work for most use cases:

- Rate limiting: 1000 calls per 5 minutes (enabled by default)
- Caching: disabled by default (see Performance & Caching section above to enable)

Customize these settings before creating a client instance if needed:

```python
>>> from usaspending import config as usaspending_config
>>> 
>>> # Configure settings before creating the client
>>> usaspending_config.configure(
...     # Cache settings (caching is disabled by default)
...     cache_enabled=True,           # Enable caching
...     # Set file-cache directory (default: ~/.usaspending_cache)
...     cache_dir="/tmp/usaspending_cache",
...     # Set cache expiration time (default 1 week)
...     cache_ttl=86400,
...     # Set cache strategy to be in-memory "mem" or "file" for file-based caching via pickle (default: "file")
...     cache_strategy="mem",
...
...     # Set rate limiting parameters
...     # Set number of calls allowed within the rate limit period (default: 1000)
...     rate_limit_calls=500,
...     # Rate limit period (in seconds, default: 300)
...     rate_limit_period=60,
...
...     # Set HTTP request parameters (default: max_retries=3, timeout=30)
...     # Set number of retries for failed requests (default: 3)
...     max_retries=5,
...     # Set delay between retries in seconds (default: 1.0)
...     retry_delay=10.0,
...     # Set exponential backoff factor for retries (default: 2.0)
...     retry_backoff=2.0,
...     # Set request timeout in seconds (default: 30)
...     timeout=60  # Longer timeout for slow connections (default: 30)
... )
>>> 
>>> # Now create the client with your configuration
>>> client = USASpendingClient()
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

with USASpendingClient() as client:
    awards = client.awards.search().contracts().all()
```

## Project Status

USASpending Python Wrapper is under active development. The API is stabilizing but may change as we refine the abstractions based on real-world usage. We welcome feedback on the interface design and feature priorities.

## Contributing

We welcome contributions to improve and expand the implementation and functionality.

## About The Planetary Society

This library was initially developed to serve the needs of The Planetary Society's Space Policy and Advocacy team in tracking and analyzing NASA contract data. We have open-sourced the project for the benefit of the broader community. [The Planetary Society](planetary.org) is a nonprofit, independent organization that empowers the world's citizens to advance space science and exploration. The organization is supported by individuals across the world, and does not accept government grants nor does it have major aerospace donations.

Please consider supporting our work by [becoming a member](https://www.planetary.org/join).

## License

MIT License