# USAspending terminology

USASpending ORM uses USAspending's domain language while presenting it through
Python-friendly names. These definitions summarize the concepts needed to use
the library; the federal source remains authoritative.

## Award

A prime award is an agreement through which a federal agency provides money to
a non-federal recipient. USAspending groups award types into contracts,
Indefinite Delivery Vehicles, grants, direct payments, loans, and other
assistance.

## Transaction

A transaction is an action reported against an award. It may create the award,
add funding, change terms, record an outlay-related field, or remove previously
obligated funding.

## Obligation and outlay

An **obligation** is a legally binding commitment by the government. An
**outlay** records money paid. They are not interchangeable, and not every
endpoint exposes both.

## Recipient

The recipient is the organization or individual receiving a prime award.
USAspending recipient identifiers can represent parent and child levels of an
organization.

## Awarding and funding agencies

The awarding agency administers the award. The funding agency supplies the
funds. Either may have top-tier, sub-tier, and office levels.

## Federal accounts and Treasury Account Symbols

A federal account groups related appropriations for budget presentation. A
Treasury Account Symbol identifies a more specific account through components
such as agency identifier, main account code, sub-account code, and period of
availability.

## Fiscal year

The federal fiscal year begins October 1 and is named for the calendar year in
which it ends. Fiscal year 2026 runs from October 1, 2025 through September 30, 2026.

## Canonical references

- [USAspending introductory API tutorial](https://api.usaspending.gov/docs/intro-tutorial)
- [USAspending endpoint index](https://api.usaspending.gov/docs/endpoints)
- [USAspending glossary](https://www.usaspending.gov/glossary)
- [USAspending data dictionary endpoint](https://api.usaspending.gov/api/v2/references/data_dictionary/)
- [Upstream search-filter contract](https://github.com/fedspendingtransparency/usaspending-api/blob/master/usaspending_api/api_contracts/search_filters.md)
