# USASpending Python Wrapper

An opinionated Python client for the USAspending.gov API that simplifies federal spending data analysis through intuitive abstractions and smart defaults.

## Overview

USASpending Python Wrapper provides a streamlined interface to the USAspending.gov API, focusing on the most common use cases while hiding the complexity of the underlying API. Rather than exposing every endpoint and parameter, this library offers a curated subset of functionality that covers the majority of real-world needs.

## Key Features

**🎯 Opinionated Design** - Pre-configured with sensible defaults for common federal spending analysis tasks. No need to understand the entire USAspending API surface.

**🔄 Lazy Loading** - Data is fetched only when needed, minimizing API calls and improving performance. Related objects (awards → recipients → locations) are loaded transparently.

**📊 Rich Data Models** - Work with intuitive Python objects instead of raw JSON. Navigate relationships naturally without manual ID lookups.

**🏛️ Geographic Analysis** - Built-in support for state and congressional district analysis. Easily aggregate spending by location with automatic political boundary awareness.

**🚀 NASA-Focused** - Special support for NASA spending analysis including subaccount breakdowns (Science, Exploration, Space Operations, etc.) and agency-specific helpers.

**💾 Smart Caching** - Automatic caching reduces redundant API calls while keeping data fresh. Configurable cache policies for different use cases.

**🔁 Automatic Retry** - Resilient to transient failures with exponential backoff and rate limit handling. Your scripts keep running even when the API hiccups.

## Philosophy

This library takes an opinionated stance on how to work with federal spending data:

- **Convention over Configuration** - Most users want to analyze recent spending by agencies in specific locations. The API is optimized for these patterns.

- **Pareto Principle** - 80% of use cases need only 20% of the API's functionality. We focus on that crucial 20%.

- **Fail Gracefully** - Government data is messy. The library handles missing fields, inconsistent formats, and API quirks automatically.

- **Performance by Default** - Lazy loading, intelligent caching, and automatic pagination work together seamlessly.

## Target Audience

USASpending Python Wrapper is ideal for:

- Policy analysts tracking federal spending in specific states or districts
- Researchers studying government contractor relationships
- Journalists investigating federal procurement patterns
- Citizens monitoring local federal investments
- Organizations analyzing agency-specific spending trends

## What This Library Doesn't Do

In keeping with its opinionated nature, USASpending Python Wrapper intentionally omits:

- Advanced transaction-level analysis
- Bulk data exports
- Every possible API filter combination
- Real-time spending alerts
- Historical data beyond recent fiscal years

For these advanced use cases, consider using the official USAspending API directly.

## Design Principles

**Simplicity First** - Common tasks should be trivial. Complex tasks should be possible.

**Intuitive Navigation** - Follow the money through natural object relationships.

**Defensive Programming** - Gracefully handle the inconsistencies inherent in government data.

**Minimal Configuration** - Start analyzing data immediately with zero configuration.

## Project Status

USASpending Python Wrapper is under active development. The API is stabilizing but may change as we refine the abstractions based on real-world usage. We welcome feedback on the interface design and feature priorities.

## Contributing

We welcome contributions that align with the library's opinionated philosophy. Before adding new features, consider whether they serve common use cases or add complexity for edge cases.

## License

MIT License - Use freely in your federal spending analysis projects.

---

*USASpending Python Wrapper is an independent project and is not affiliated with or endorsed by USAspending.gov or the U.S. Department of the Treasury.*