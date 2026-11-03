# Queries and filters

Query builders provide lazy execution, pagination, limits, counting, indexing,
and fluent filter methods. See [Query execution](../explanation/query-execution.md)
for the behavioral model.

## Award search

::: usaspending.AwardsSearch

## Global transaction search

::: usaspending.TransactionsSearch

## Award-scoped transaction search

::: usaspending.AwardTransactionsSearch

## Subaward search

::: usaspending.SubAwardsSearch

## Recipient search

::: usaspending.RecipientsSearch

## Agency searches

::: usaspending.AgenciesSearch

::: usaspending.AwardingAgenciesSearch

::: usaspending.FundingAgenciesSearch

## Funding and spending searches

::: usaspending.FundingSearch

::: usaspending.SpendingSearch

## Reference data

These queries fetch one reference list and filter it in memory. Code matching
uses `.code()` or `.codes()`; `.description()` searches country/state names and
DEFC descriptions case-insensitively. See [Core concepts](../getting-started/core-concepts.md#reference-data)
for a combined example.

::: usaspending.queries.DefCodesQuery

::: usaspending.queries.CountriesQuery

::: usaspending.queries.StatesQuery

## Filter value objects

::: usaspending.AgencyFilter

::: usaspending.AwardAmountFilter

::: usaspending.KeywordsFilter

::: usaspending.LocationFilter

::: usaspending.LocationSpec

::: usaspending.TimePeriodFilter

::: usaspending.TreasuryAccountComponentsFilter
