# USAspending data model

The library presents several related grains of federal spending data.

## Prime awards

An award is the durable agreement between the federal government and a
recipient: a contract, grant, loan, direct payment, other assistance, or
Indefinite Delivery Vehicle. An award accumulates financial activity over its
lifetime.

`Award` and its subclasses normalize the details endpoint and expose
relationships such as recipient, agencies, period of performance, place of
performance, transactions, accounts, funding records, and subawards.

## Transactions

A transaction is an action that changes or reports an award. Examples include
the initial obligation, a contract modification, an incremental funding
action, or a deobligation.

Transaction searches therefore have a different grain from award searches:

- award search returns one row per matching award;
- global transaction search returns one row per matching action;
- `award.transactions` returns actions belonging to one award.

Summing transaction amounts and reading an award's current total obligation are
different analytical operations.

## Subawards

A subaward records funding passed from a prime recipient to another
organization. Subawards are reported separately and do not share every field or
filter available for prime awards.

## Accounts and funding records

Federal accounts and Treasury Account Symbols describe the appropriations
accounts behind spending. Award funding records connect transactions to those
accounts and agencies. These records are useful when the question concerns
budget authority or the source of funds rather than only the recipient and
award.

## Aggregations

Spending-by-category endpoints return grouped totals by dimensions such as
recipient or geography. Their rows are summaries, not awards, and use dedicated
models.

See [Terminology](../usaspending-api/terminology.md) for links to canonical
USAspending definitions.
