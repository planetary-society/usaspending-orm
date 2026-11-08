# Supported endpoint mapping

This page maps public library workflows to the canonical USAspending API
contracts. It intentionally lists the supported subset rather than mirroring
USAspending's complete endpoint catalog.

Last reviewed against the upstream contracts: **November 3, 2026**.

## Search and detail operations

| Library workflow                                  | USAspending endpoint                                 | Contract and wrapper notes                                                                                                                                                                                                            |
| ------------------------------------------------- | ---------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `client.awards.search()`                          | `POST /api/v2/search/spending_by_award/`             | [Contract](https://github.com/fedspendingtransparency/usaspending-api/blob/master/usaspending_api/api_contracts/contracts/v2/search/spending_by_award.md). Returns one prime award per row and requires a single award-type category. |
| `client.awards.search().count()`                  | `POST /api/v2/search/spending_by_award_count/`       | [Contract](https://github.com/fedspendingtransparency/usaspending-api/blob/master/usaspending_api/api_contracts/contracts/v2/search/spending_by_award_count.md). Category buckets are normalized into one count.                      |
| `client.awards.find_by_award_id(...)`             | `GET /api/v2/awards/{award_id}/`                     | [Contract](https://github.com/fedspendingtransparency/usaspending-api/blob/master/usaspending_api/api_contracts/contracts/v2/awards/award_id.md). Produces the appropriate award subclass.                                            |
| `client.transactions.search()`                    | `POST /api/v2/search/spending_by_transaction/`       | [Contract](https://github.com/fedspendingtransparency/usaspending-api/blob/master/usaspending_api/api_contracts/contracts/v2/search/spending_by_transaction.md). Supports mixed award categories and returns global transaction rows. |
| `client.transactions.search().count()`            | `POST /api/v2/search/spending_by_transaction_count/` | [Contract](https://github.com/fedspendingtransparency/usaspending-api/blob/master/usaspending_api/api_contracts/contracts/v2/search/spending_by_transaction_count.md). The library sums only selected award-category buckets.         |
| `award.transactions`                              | `POST /api/v2/transactions/`                         | [Contract](https://github.com/fedspendingtransparency/usaspending-api/blob/master/usaspending_api/api_contracts/contracts/v2/transactions.md). Lists actions for one generated award ID.                                              |
| `award.transactions.count()`                      | `GET /api/v2/awards/count/transaction/{award_id}/`   | [Contract](https://github.com/fedspendingtransparency/usaspending-api/blob/master/usaspending_api/api_contracts/contracts/v2/awards/count/transaction/award_id.md).                                                                   |
| `client.subawards.search()` and `award.subawards` | `POST /api/v2/search/spending_by_award/`             | Uses `spending_level=subawards`; the response is normalized into `SubAward` models.                                                                                                                                                   |
| `award.subawards.count()`                         | `POST /api/v2/search/spending_by_award_count/`       | Sends `spending_level=subawards` with the query's filters, including `award_unique_id`; the library sums the `subcontracts` and `subgrants` buckets.                                                                                  |
| `award.funding`                                   | `POST /api/v2/awards/funding/`                       | [Contract](https://github.com/fedspendingtransparency/usaspending-api/blob/master/usaspending_api/api_contracts/contracts/v2/awards/funding.md). Connects transactions to accounts and funding agencies.                              |
| `award.accounts`                                  | `POST /api/v2/awards/accounts/`                      | [Contract](https://github.com/fedspendingtransparency/usaspending-api/blob/master/usaspending_api/api_contracts/contracts/v2/awards/accounts.md).                                                                                     |
| `idv.child_awards`                                | `POST /api/v2/idvs/awards/`                          | [Contract](https://github.com/fedspendingtransparency/usaspending-api/blob/master/usaspending_api/api_contracts/contracts/v2/idvs/awards.md).                                                                                         |

## Subaward summary search

| Library workflow | USAspending endpoint | Contract and wrapper notes |
| --- | --- | --- |
| `client.awards.subaward_summary()` | `POST /api/v2/search/spending_by_subaward_grouped/` | [Contract](https://github.com/fedspendingtransparency/usaspending-api/blob/master/usaspending_api/api_contracts/contracts/v2/search/spending_by_subaward_grouped.md). Prime-award filters select whole-award subaward totals, including zero-subaward rows; mixed award categories are supported. |
| `client.awards.subaward_summary().count()` | `POST /api/v2/search/spending_by_award_count/` | Sums all six category buckets using the same filters. Counting does not page through the summary endpoint. |

## Recipients, agencies, and accounts

| Library workflow                                          | USAspending endpoint                                                 | Contract and wrapper notes                                                                                                                                            |
| --------------------------------------------------------- | -------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `client.recipients.search()`                              | `POST /api/v2/recipient/`                                            | Returns recipient records and supports the companion count operation.                                                                                                 |
| `client.recipients.find_by_recipient_id(...)`             | `GET /api/v2/recipient/{recipient_id}/`                              | [Contract](https://github.com/fedspendingtransparency/usaspending-api/blob/master/usaspending_api/api_contracts/contracts/v2/recipient/recipient_id.md).              |
| `client.agencies.find_by_toptier_code(...)`               | `GET /api/v2/agency/{toptier_code}/`                                 | Returns the overview used by the USAspending agency profile.                                                                                                          |
| `agency.total_obligations` and `agency.transaction_count` | `GET /api/v2/agency/{toptier_code}/awards/`                          | Lazy properties use the agency award summary when the overview row does not carry those values.                                                                       |
| `agency.subagencies`                                      | `GET /api/v2/agency/{toptier_code}/sub_agency/`                      | Returns sub-tier agencies and offices.                                                                                                                                |
| `client.agencies.search().agency_type("awarding")`        | `POST /api/v2/autocomplete/awarding_agency_office/`                  | [Contract](https://github.com/fedspendingtransparency/usaspending-api/blob/master/usaspending_api/api_contracts/contracts/v2/autocomplete/awarding_agency_office.md). |
| `client.agencies.search().agency_type("funding")`         | `POST /api/v2/autocomplete/funding_agency_office/`                   | [Contract](https://github.com/fedspendingtransparency/usaspending-api/blob/master/usaspending_api/api_contracts/contracts/v2/autocomplete/funding_agency_office.md).  |
| `client.references.def_codes()`                           | `GET /api/v2/references/def_codes/`                                  | Returns a lazy `DefCodesQuery` over the API's current Disaster Emergency Fund Code reference data as `DefCode` models.                                               |
| `client.references.countries()`                           | `GET /api/v2/references/countries/`                                  | [Contract](https://github.com/fedspendingtransparency/usaspending-api/blob/master/usaspending_api/api_contracts/contracts/v2/references/countries.md). Returns a lazy `CountriesQuery` of `Country` records, preserving special location codes. |
| `client.references.states()`                              | `GET /api/v2/references/states/`                                     | [Contract](https://github.com/fedspendingtransparency/usaspending-api/blob/master/usaspending_api/api_contracts/contracts/v2/references/states.md). Returns a lazy `StatesQuery` of `State` records with string FIPS codes. |
| `client.tas.agencies`                                     | `GET /api/v2/references/filter_tree/tas/`                            | [Contract](https://github.com/fedspendingtransparency/usaspending-api/blob/master/usaspending_api/api_contracts/contracts/v2/references/filter_tree/tas.md).          |
| `agency.federal_accounts`                                 | `GET /api/v2/references/filter_tree/tas/{agency}/`                   | Returns federal accounts under an agency.                                                                                                                             |
| `federal_account.tas_codes`                               | `GET /api/v2/references/filter_tree/tas/{agency}/{federal_account}/` | Returns Treasury Account Symbols under a federal account.                                                                                                             |

## Aggregations and downloads

| Library workflow                                                  | USAspending endpoint                                          | Contract and wrapper notes                                                                                                                                                    |
| ----------------------------------------------------------------- | ------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `client.spending.search().by_recipient()`                         | `POST /api/v2/search/spending_by_category/recipient/`         | [Contract](https://github.com/fedspendingtransparency/usaspending-api/blob/master/usaspending_api/api_contracts/contracts/v2/search/spending_by_category/recipient.md).       |
| `client.spending.search().by_state()`                             | `POST /api/v2/search/spending_by_category/state_territory/`   | [Contract](https://github.com/fedspendingtransparency/usaspending-api/blob/master/usaspending_api/api_contracts/contracts/v2/search/spending_by_category/state_territory.md). |
| `client.spending.search().by_district()`                          | `POST /api/v2/search/spending_by_category/district/`          | [Contract](https://github.com/fedspendingtransparency/usaspending-api/blob/master/usaspending_api/api_contracts/contracts/v2/search/spending_by_category/district.md).        |
| `client.downloads.search(...)`                                    | `POST /api/v2/download/search/`                               | Creates a server-side award, transaction, and/or subaward export.                                                                                                             |
| `award.download()`                                                | `POST /api/v2/download/contract/`, `/assistance/`, or `/idv/` | Chooses the endpoint from the award type.                                                                                                                                     |
| `DownloadJob.refresh_status()` and `client.downloads.status(...)` | `GET /api/v2/download/status/`                                | Polls an asynchronous export job.                                                                                                                                             |

## Reviewed upstream behavior

The August 3 to November 3, 2026 review also covered these server changes. They
require no wrapper code:

- Award funding and account endpoints omit submissions until their reveal
  dates. Related totals can change when submissions become public
  ([upstream change](https://github.com/fedspendingtransparency/usaspending-api/commit/b4595d9)).
- `award_ids` matching now escapes regex metacharacters such as `.` and `@`
  more strictly, so identifiers containing them may match fewer awards
  ([upstream change](https://github.com/fedspendingtransparency/usaspending-api/commit/54e2019)).
- Search-download filenames vary with `spending_level`, and repeated levels
  are deduplicated by the server. The wrapper already uses server-provided
  filenames ([filename change](https://github.com/fedspendingtransparency/usaspending-api/commit/6e06506),
  [deduplication change](https://github.com/fedspendingtransparency/usaspending-api/commit/281c978)).
- LLM integration remains deferred: its endpoint requires an API key, and it
  does not change any endpoint this library wraps.

For the complete federal endpoint catalog, use the
[USAspending endpoint index](https://api.usaspending.gov/docs/endpoints).
