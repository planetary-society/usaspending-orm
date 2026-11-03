# Models

Models normalize upstream field names, parse common types, retain the source
response in `.raw`, and expose selected relationships. Reference records are
simple dataclasses containing the API's reference fields.

## Awards

::: usaspending.Award

::: usaspending.Contract

::: usaspending.Grant

::: usaspending.Loan

::: usaspending.IDV

## Transactions, funding, and subawards

::: usaspending.Transaction

::: usaspending.Funding

::: usaspending.SubAward

::: usaspending.SubAwardSummary

## Organizations

::: usaspending.Recipient

::: usaspending.Agency

::: usaspending.SubTierAgency

## Places and periods

::: usaspending.Location

::: usaspending.PeriodOfPerformance

## Aggregated spending

::: usaspending.Spending

::: usaspending.RecipientSpending

::: usaspending.StateSpending

::: usaspending.DistrictSpending

## Reference data

::: usaspending.models.DefCode

::: usaspending.models.Country

::: usaspending.models.State
