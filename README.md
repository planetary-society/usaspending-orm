# USASpending ORM

An opinionated Python wrapper for the USAspending.gov API that applies an object-relational mapping layer to simplify access to the underlying data.

## Key Features

**🔗 ORM-Style Chained Interface** - Applies relational object mapping to the USASpending API to simplify data access and preocessing using a clean, intuitive syntax inspired by ActiveRecord (e.g., `award.recipient.location.city`).

**🔎 Comprehensive Award Queries** - Construct complex queries in using a chainable interface that maps to the set of Award filters provided by the API. Filter by agencies, award types, fiscal years, and more without wrestling with raw API parameters.

**⚡️ Smart Caching & Rate Limiting** - Out-of-the-box file caching speeds up repeated requests, while automatic rate limiting ensures your application stays within the API's usage limits.

**📄 Transparent Pagination** - Seamlessly iterate through thousands of records. The library handles the underlying pagination, letting you treat large result sets like standard Python lists.

**🛡️ Data Normalization and Type Casting** - Normalizes inconsistent property names and gracefully handles missing fields via lazy-loading of attributes. Casts values to proper types.

**🥩 Raw API Output is Still There** - Access the raw API JSON values and structure via the `.raw` property on any ORM class object.

## Usage

No API key is required to use the USASpending.gov API resource. Just install, import, configure, and use.

### Load and configure the client
```python
>>> from usaspending import USASpendingClient
>>> client = USASpendingClient()
```

### Load a single award
```python
>>> award = client.awards.find_by_award_id("80GSFC18C0008")
>>> award.category
'contract'
>>> award.total_obligation
Decimal('172213419.67')
```

### Access properties and queries via chained object associations
```python
>>> print(award.recipient.location.full_address)
105 Jessup Hall
Iowa City, IA, 52242
United States

>>> award.subawards.count()
100

>>> award.subawards[2].recipient.place_of_performance.district
'AL-03'
```

### Search for awards using the full filter set from the API
```python
# Search for all active contracts for NASA in FY 2022
>>> award_query = client.awards.search() \
...             .for_agency("National Aeronautics and Space Administration") \ 
...             .contracts() \
...             .for_fiscal_year(2022)

>>> award_query.count()
11358

# Includes ordering by any search field
>>> award_query.order_by("Award Amount","desc")

# API query is not executed until results are needed
>>> awards = award_query.all() # Executes the query and fetches all results

>>> awards[0].total_obligation
Decimal(22163800679.69)
```

### Queries are iterable
```python

>>> len(award_query)
11358

>>> award = award_query[5000]
>>> for transaction in award.transactions:
...     print(f"{transaction.action_date}: {transaction.federal_action_obligation}")
```

### Custom Configuration

You can customize the library's behavior before creating a client instance:

```python
>>> from usaspending import USASpendingClient, config
>>> 
>>> # Configure settings before creating the client
>>> config.configure(
...     logging_level="DEBUG",  # Increase log verbosity (default: "INFO")
...     cache_dir="/tmp/usaspending_cache",  # Custom cache location
...     cache_ttl=86400,  # Cache for 24 hours (default: 1 week)
...     max_retries=5,  # Increase retry attempts (default: 3)
...     timeout=60  # Longer timeout for slow connections (default: 30)
... )
>>> 
>>> # Now create the client with your configuration
>>> client = USASpendingClient()
```

## Project Status

USASpending Python Wrapper is under active development. The API is stabilizing but may change as we refine the abstractions based on real-world usage. We welcome feedback on the interface design and feature priorities.

## Contributing

We welcome contributions to improve and expand the implementation and functionality.

## License

MIT License