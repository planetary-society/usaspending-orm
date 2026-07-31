# Configuration and errors

## Global configuration

Import the shared `config` object and call `config.configure(...)` before
creating clients.

```python
from datetime import timedelta

from usaspending import config

config.configure(
    timeout=45,
    max_retries=4,
    cache_enabled=True,
    cache_ttl=timedelta(hours=12),
    default_result_limit=5000,
)
```

Important settings include:

| Setting                 |            Default | Meaning                                      |
| ----------------------- | -----------------: | -------------------------------------------- |
| `base_url`              | USAspending API v2 | API root used by new clients                 |
| `timeout`               |               `30` | Request timeout in seconds                   |
| `max_retries`           |                `3` | Maximum retry attempts                       |
| `retry_delay`           |             `10.0` | Base seconds between retries, before backoff |
| `rate_limit_calls`      |             `1000` | Calls allowed in one local rate-limit period |
| `rate_limit_period`     |              `300` | Local rate-limit period in seconds           |
| `session_request_limit` |              `250` | Requests before the HTTP session is renewed  |
| `default_result_limit`  |            `10000` | Safety bound for query iteration             |
| `cache_enabled`         |            `False` | Enable or disable response caching           |
| `cache_backend`         |           `"file"` | `"file"` or `"memory"`                       |
| `cache_ttl`             |           one week | Lifetime of cached responses                 |

Unknown setting names are ignored with a warning. Invalid known values raise
`ConfigurationError`.

## Exception hierarchy

Catch `USASpendingError` to handle every library-specific failure, or catch a
subclass when recovery differs.

::: usaspending.USASpendingError

::: usaspending.ValidationError

::: usaspending.APIError

::: usaspending.HTTPError

::: usaspending.RateLimitError

::: usaspending.DetachedInstanceError

::: usaspending.ConfigurationError

::: usaspending.DownloadError
