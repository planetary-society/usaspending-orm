# Caching

Caching is off by default. When enabled, the client stores successful API
responses and serves repeat requests from the store instead of the network.

```python
from datetime import timedelta

from usaspending import USASpendingClient, config

config.configure(
    cache_enabled=True,
    cache_backend="file",
    cache_ttl=timedelta(days=1),
)

with USASpendingClient() as client:
    award = client.awards.find_by_award_id("80GSFC18C0008")
```

Configure caching before creating a client. Settings are applied through an
observer, so a later `configure()` call rebuilds the cache wrapper rather than
leaving clients on stale settings.

## What gets cached

The unit of caching is one HTTP request, not one query. A cache entry is keyed
on the endpoint and the full request payload, so two searches that differ in any
filter, sort, or page are separate entries, and a repeat of the identical
request is a hit.

Because the unit is the request, caching covers everything the library sends:
search pages, count calls, award detail lookups, and the follow-up requests
behind lazy relationships. A loop that reads `award.recipient.location` for many
awards still issues one request per award the first time, but pays nothing on a
second pass over the same awards.

Two things are deliberately not stored:

- **Failures.** Errors are never cached, so a transient outage does not poison
  the store. The next call re-issues the request.
- **Empty results.** A response the client could not interpret is not stored,
  and the request falls back to the network.

## Cache misses are never fatal

Reading from the cache is best-effort. If the store is unreadable, locked, or
corrupt, the client logs a warning and issues the request normally. A broken
cache degrades performance, never correctness.

API errors are the exception to that fallback: `APIError`, `HTTPError`,
`RateLimitError`, and `ValidationError` propagate to the caller rather than
being retried uncached, because they describe the request rather than the cache.

## Backends

`cache_backend="memory"` keeps entries in the process and discards them on exit.
It suits tests and short scripts, and avoids writing anything to disk.

`cache_backend="file"` is the default and writes pickled responses under
`cache_dir`, which defaults to `$XDG_CACHE_HOME/usaspending` or
`~/.cache/usaspending`. Entries survive the process, so a later run reuses what
an earlier one fetched. That is what makes an interrupted batch job cheap to
restart, and what lets a script re-run during development stop paying for the
same pages.

Reuse depends on the request serializing identically each time. The library
sorts the values of match-any filters for that reason, so a filter built from a
Python set produces the same request, and therefore the same cache entry, on
every run.

!!! warning "The file backend unpickles data it reads"

    Unpickling executes code, so the cache directory is a trust boundary. The
    library creates it with `0700` permissions and restores those permissions if
    they have been widened, but do not point `cache_dir` at a shared,
    world-writable, or otherwise untrusted location, and do not use a directory
    another user can write to.

## Expiry and namespaces

`cache_ttl` sets how long an entry stays fresh; the default is one week. An
entry older than the TTL is recomputed on next use. `configure()` accepts either
a `timedelta` or a number of seconds.

Federal spending data is revised after publication, so the TTL is a correctness
decision as much as a performance one. A long TTL on a reporting job can serve
figures that agencies have since corrected. Prefer hours or days for anything
whose numbers get published, and reserve a week for exploratory work.

`cache_namespace` is part of every key, so two projects sharing a `cache_dir` do
not read each other's entries. Change it to isolate a workload, or to abandon an
existing set of entries wholesale.

`cache_timeout` bounds how long a caller waits for another worker that is
already computing the same entry, which keeps concurrent callers from
stampeding the same request.

## Clearing the cache

There is no public API for clearing the cache. With the file backend, delete the
files under `cache_dir`; with the memory backend, ending the process is enough.
Changing `cache_namespace` also abandons the previous entries without deleting
them.

## Choosing a TTL

- Interactive analysis over a stable slice of history: hours to a day.
- Repeatedly re-running the same broad query while developing: a day or more,
  since the point is to stop paying for the same pages.
- Anything producing published figures: short, or disabled, so a correction
  upstream is not masked by a stale entry.

See [Production use](../guides/production.md) for how caching interacts with
rate limiting and long batch runs.
