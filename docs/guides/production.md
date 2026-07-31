# Production use

## Configure before creating clients

The global `config` object controls timeouts, retries, rate limiting, caching,
session renewal, and default result bounds:

```python
from datetime import timedelta

from usaspending import USASpendingClient, config

config.configure(
    timeout=45,
    max_retries=4,
    cache_enabled=True,
    cache_backend="file",
    cache_ttl=timedelta(days=1),
    default_result_limit=5000,
)

with USASpendingClient() as client:
    award = client.awards.find_by_award_id("80GSFC18C0008")
```

Configure settings before creating clients so cache wrappers and request
behavior are consistent.

## Caching

Caching is disabled by default. Enabling it makes repeat requests free, which
matters most when a job re-reads the same awards or re-runs the same searches.
The file backend stores pickled responses in a private cache directory; do not
point it at a shared or untrusted location. Use the memory backend when nothing
should touch disk.

Pick the TTL deliberately: federal data is revised after publication, so a long
TTL can serve figures that agencies have since corrected. See
[Caching](../explanation/caching.md) for what gets cached, the backends, and
how entries expire.

## Errors

Catch the narrowest useful exception:

```python
from usaspending import (
    APIError,
    HTTPError,
    RateLimitError,
    USASpendingClient,
    ValidationError,
)

try:
    with USASpendingClient() as client:
        result = client.awards.search().contracts().fiscal_year(2024).first()
except ValidationError as error:
    print(f"Invalid query: {error}")
except RateLimitError as error:
    print(f"Rate limited: {error}")
except HTTPError as error:
    print(f"Network or server failure: {error}")
except APIError as error:
    print(f"USAspending rejected the request: {error}")
```

`ValidationError` indicates a caller error and is not retried. Transport and
selected server failures use the configured retry policy.

## Long batch runs

A job that sweeps many queries hits different limits from an interactive one.
The defaults are tuned for interactive use; for a long unattended sweep,
throttle below them and make the run resumable:

```python
config.configure(
    cache_enabled=True,
    rate_limit_calls=1,
    rate_limit_period=1,
    retry_delay=60.0,
    session_request_limit=100,
)
```

- Pacing to roughly one request per second trades wall-clock time for a run
  that finishes rather than one that stalls on repeated retries.
- A longer `retry_delay` suits a job that can afford to wait out a transient
  upstream failure.
- A lower `session_request_limit` renews the HTTP session more often, which
  avoids long-lived connections going stale mid-sweep.
- Caching makes a resumed run skip the network for work the previous run already
  did, since file-backend entries outlive the process. Record progress as you go
  anyway, so an interrupted sweep restarts from the last completed unit rather
  than replaying everything from the beginning against the cache.

## Result bounds and request volume

- Keep `.limit()` explicit in interactive and web-facing workloads.
- Use `.count()` before fetching only when the count is needed; it is another
  request.
- Avoid reading lazy relationships in large loops.
- Use bulk downloads for comprehensive extracts.
- Log enough query context to reproduce failures, but never log secrets or
  private data alongside cached response payloads.
