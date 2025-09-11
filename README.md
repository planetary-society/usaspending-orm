# USASpending ORM

A wrapper for the USAspending.gov API that applies an object-relational mapping layer to simplify access to the underlying spending data.

[USASpending.gov](https://usaspending.gov) is the official federal database for tracking U.S. government spending, established by Federal Funding Accountability and Transparency Act of 2006. The platform provides extensive data on federal contracts, grants, and other awards since 2007-10-01, enabling citizens to track how federal money is spent.

The platform provides access to a comprehensive API for querying the data, but the API can be complex and cumbersome to work with directly. This library provides an abstraction layer that focuses on common and provide a clean, Pythonic interface for accessing and processing the data.

## Key Features

**🔗 ORM-Style Chained Interface** - Applies relational object mapping to the USASpending API to simplify data access and preocessing using a clean, intuitive syntax inspired by ActiveRecord (e.g., `award.recipient.location.city`).

**🔎 Comprehensive Award Queries** - Construct complex queries in using a chainable interface that maps to the set of Award filters provided by the API. Filter by agencies, award types, fiscal years, and more without wrestling with raw API parameters.

**⚡️ Smart Caching & Rate Limiting** - Out-of-the-box file caching speeds up repeated requests, while automatic rate limiting ensures your application stays within the API's usage limits.

**📄 Transparent Pagination** - Seamlessly iterate through thousands of records. The library handles the underlying pagination, letting you treat large result sets like standard Python lists.

**🛡️ Data Normalization and Type Casting** - Normalizes inconsistent property names and gracefully handles missing fields via lazy-loading of attributes. Casts values to proper types.

**🥩 Raw API Output is Still There** - Access the raw API JSON values and structure via the `.raw` property on any ORM resource object.

## Usage

No API key is required to use the USASpending.gov API resource. Just install, import, configure, and use.

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

### Search for awards using the full filter set from the API
```python
# Search for all active contracts for NASA in FY 2022
>>> with USASpendingClient() as client:
...     award_query = client.awards.search() \
...                 .for_agency("National Aeronautics and Space Administration") \
...                 .contracts() \
...                 .for_fiscal_year(2022)
...
...     # Get total number of matching awards
...     award_query.count()
...     
...     # Includes ordering by any search field
...     award_query = award_query.order_by("Award Amount", "desc")
...     
...     # API query is not executed until results are needed
...     awards = award_query.all()  # Executes the query and fetches all results
```

### Queries are iterable
```python
>>> with USASpendingClient() as client:
...     award_query = client.awards.search() \
...                 .for_agency("National Aeronautics and Space Administration") \
...                 .contracts() \
...                 .for_fiscal_year(2022)
...     
...     print(f"Query length: {len(award_query)}")
...     
...     # Access specific award by index
...     award = award_query[5000]
...     for transaction in award.transactions[:3]:  # Show first 3 transactions
...         print(f"{transaction.action_date}: ${transaction.federal_action_obligation:,.2f}")
```

### Customizable Settings

The library implements sensible defaults for API rate limiting and caching:

- Rate limiting: 1000 calls per 5 minutes
- Caching: file-based, stores successful API qeries for 1 week in a `.usaspending_cache` directory in the user's home folder

You can customize these defaults before creating a client instance. This is particularly useful for making large numbers of requests, which can trigger more aggressive rate limiting by the API.

```python
>>> from usaspending import config as usaspending_config
>>> 
>>> # Configure settings before creating the client
>>> usaspending_config.configure(
...     # Cache settings
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

### Session Management

For proper resource cleanup, use the client as a context manager (recommended) or explicitly call `close()`:

```python
# Recommended: Context manager automatically closes session
with USASpendingClient() as client:
    awards = client.awards.search().for_agency("NASA").all()
    for award in awards:
        print(f"{award.recipient_name}: ${award.total_obligation:,.2f}")
# Session automatically closed here

# Alternative: Manual cleanup
client = USASpendingClient()
try:
    awards = client.awards.search().for_agency("NASA").all()
    # Process awards...
finally:
    client.close()  # Always close to free resources
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

This library was initially developed to serve the needs of The Planetary Society's Space Policy and Advocacy team in tracking and analyzing NASA contract data. We have open-sourced the project for the benefit of the broader community. [The Planetary Society](planetary.org) is a nonprofit, independent organization that empowers the world's citizens to advance space science and exploration. The organization is supported by individuals across the world, and does not accept government grants not does it have major aerospace donations.

Please consider supporting our work by [becoming a member](https://www.planetary.org/join).

## License

MIT License