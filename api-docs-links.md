# USASpending.gov API Documentation Links

## Core API Documentation

- **API v2 Endpoints**: https://api.usaspending.gov/docs/endpoints
- **Search Filters Documentation**: https://raw.githubusercontent.com/fedspendingtransparency/usaspending-api/refs/heads/master/usaspending_api/api_contracts/search_filters.md

## Key Endpoints Used in This Project

Use web fetch to access the following official API documentation links for key endpoints utilized in this project.
These documentation links provide detailed information about request parameters, response structures, and usage examples.

### Award Search

- **Endpoint**: `/api/v2/search/spending_by_award/`
- **Method**: POST
- **Documentation**: https://raw.githubusercontent.com/fedspendingtransparency/usaspending-api/refs/heads/master/usaspending_api/api_contracts/contracts/v2/search/spending_by_award.md
- **Purpose**: Search for awards by various criteria including agency, geography, time period
- **Corresponding Query Builder**: `src/usaspending/queries/awards_search.py`
- **Note**: The endpoint accepts an optional `object_classes` filter (array of object class code strings, e.g. `["10", "252"]`), valid for awards only. The API returns HTTP 422 when `object_classes` is combined with `spending_level=subawards`.

### Award Search Count

- **Endpoint**: `/api/v2/search/spending_by_award_count/`
- **Method**: POST
- **Documentation**: https://raw.githubusercontent.com/fedspendingtransparency/usaspending-api/refs/heads/master/usaspending_api/api_contracts/contracts/v2/search/spending_by_award_count.md
- **Purpose**: Return award counts by category for advanced search filters, including subaward counts when `spending_level` is `subawards`
- **Corresponding Query Builders**: `src/usaspending/queries/awards_search.py`, `src/usaspending/queries/subawards_search.py`
- **Note**: For `spending_level=subawards`, the live API returns subaward totals under `results.subgrants` and `results.subcontracts`.
- **Note**: The endpoint accepts an optional `object_classes` filter (array of object class code strings, e.g. `["10", "252"]`), valid for awards only. The API returns HTTP 422 when `object_classes` is combined with `spending_level=subawards`.

### Spending by State/Territory

- **Endpoint**: `/api/v2/search/spending_by_category/state_territory/`
- **Method**: POST
- **Documentation**: https://raw.githubusercontent.com/fedspendingtransparency/usaspending-api/refs/heads/master/usaspending_api/api_contracts/contracts/v2/search/spending_by_category/state_territory.md
- **Purpose**: Get spending totals by a given U.S. state or territory
- **Corresponding Query Builder**: `src/usaspending/queries/spending_search.py`

### Spending by Congressional District

- **Endpoint**: `/api/v2/search/spending_by_category/district/`
- **Method**: POST
- **Documentation**: https://raw.githubusercontent.com/fedspendingtransparency/usaspending-api/refs/heads/master/usaspending_api/api_contracts/contracts/v2/search/spending_by_category/district.md
- **Purpose**: Get spending totals by a given congressional district
- **Corresponding Query Builder**: `src/usaspending/queries/spending_search.py`

### Spending by Recipient

- **Endpoint**: `/api/v2/search/spending_by_category/recipient/`
- **Method**: POST
- **Documentation**: https://raw.githubusercontent.com/fedspendingtransparency/usaspending-api/refs/heads/master/usaspending_api/api_contracts/contracts/v2/search/spending_by_category/recipient.md
- **Purpose**: Get award recipient listing with their total spending/award values
- **Corresponding Query Builder**: `src/usaspending/queries/recipients_search.py`

### Award Details

- **Endpoint**: `/api/v2/awards/{award_id}/`
- **Method**: GET
- **Documentation**: https://raw.githubusercontent.com/fedspendingtransparency/usaspending-api/refs/heads/master/usaspending_api/api_contracts/contracts/v2/awards/award_id.md
- **Purpose**: Get detailed information about a specific federal award
- **Corresponding Query Builder**: `src/usaspending/queries/award_query.py`

### Recipient Details

- **Endpoint**: `/api/v2/recipient/{recipient_id}/`
- **Method**: GET
- **Documentation**: https://raw.githubusercontent.com/fedspendingtransparency/usaspending-api/refs/heads/master/usaspending_api/api_contracts/contracts/v2/recipient/recipient_id.md
- **Purpose**: Get detailed recipient information
- **Corresponding Query Builder**: `src/usaspending/queries/recipient_query.py`

### Recipient Search Count

- **Endpoint**: `/api/v2/recipient/count/`
- **Method**: POST
- **Documentation**: https://raw.githubusercontent.com/fedspendingtransparency/usaspending-api/refs/heads/master/usaspending_api/api_contracts/contracts/v2/recipient/count.md
- **Purpose**: Return the number of recipients matching the current recipient search filters
- **Corresponding Query Builder**: `src/usaspending/queries/recipients_search.py`

### Award transactions

- **Endpoint**: `/api/v2/transactions/`
- **Method**: POST
- **Documentation**: https://raw.githubusercontent.com/fedspendingtransparency/usaspending-api/refs/heads/master/usaspending_api/api_contracts/contracts/v2/transactions.md
- **Purpose**: List obligations and modifications for a given award
- **Corresponding Query Builder**: `src/usaspending/queries/award_transactions_search.py`

### Award Transaction Count

- **Endpoint**: `/api/v2/awards/count/transaction/{award_id}/`
- **Method**: GET
- **Documentation**: https://raw.githubusercontent.com/fedspendingtransparency/usaspending-api/refs/heads/master/usaspending_api/api_contracts/contracts/v2/awards/count/transaction/award_id.md
- **Purpose**: Return the number of transactions associated with a given award
- **Corresponding Query Builder**: `src/usaspending/queries/award_transactions_search.py`

### Award funding history

- **Endpoint**: `/api/v2/awards/funding/`
- **Method**: POST
- **Documentation**: https://raw.githubusercontent.com/fedspendingtransparency/usaspending-api/refs/heads/master/usaspending_api/api_contracts/contracts/v2/awards/funding.md
- **Purpose**: Get funding history (obligations and outlays) for a given award
- **Corresponding Query Builder**: `src/usaspending/queries/funding_search.py`

### Award Federal Accounts

- **Endpoint**: `/api/v2/awards/accounts/`
- **Method**: POST
- **Documentation**: https://raw.githubusercontent.com/fedspendingtransparency/usaspending-api/refs/heads/master/usaspending_api/api_contracts/contracts/v2/awards/accounts.md
- **Purpose**: List federal accounts associated with a given award
- **Corresponding Query Builder**: `src/usaspending/queries/award_accounts_query.py`

### Subawards

- **Endpoint**: `/api/v2/search/spending_by_award/`
- **Method**: POST
- **Documentation**: https://raw.githubusercontent.com/fedspendingtransparency/usaspending-api/refs/heads/master/usaspending_api/api_contracts/contracts/v2/search/spending_by_award.md
- **Purpose**: List subawards matching a set of search filters
- **Corresponding Query Builder**: `src/usaspending/queries/subawards_search.py`
- **Note**: `SubAwardsSearch` inherits `AwardsSearch` and POSTs the same `/api/v2/search/spending_by_award/` endpoint, adding `subawards=true` and `spending_level=subawards` to the payload. It does not call `/api/v2/subawards/`. Award-scoped requests set `filters.award_unique_id` to the generated award ID, and `count()` for a specific award uses the `/api/v2/awards/count/subaward/{award_id}/` endpoint.

### Award Subaward Count

- **Endpoint**: `/api/v2/awards/count/subaward/{award_id}/`
- **Method**: GET
- **Documentation**: https://raw.githubusercontent.com/fedspendingtransparency/usaspending-api/refs/heads/master/usaspending_api/api_contracts/contracts/v2/awards/count/subaward/award_id.md
- **Purpose**: Return the number of subawards associated with a given award
- **Corresponding Query Builder**: `src/usaspending/queries/subawards_search.py`

### IDV Child Awards

- **Endpoint**: `/api/v2/idvs/awards/`
- **Method**: POST
- **Documentation**: https://raw.githubusercontent.com/fedspendingtransparency/usaspending-api/refs/heads/master/usaspending_api/api_contracts/contracts/v2/idvs/awards.md
- **Purpose**: List child awards (delivery orders and task orders) placed against a parent Indefinite Delivery Vehicle (IDV)
- **Corresponding Query Builder**: `src/usaspending/queries/idv_child_awards.py`

### Agency Overview

- **Endpoint**: `/api/v2/agency/{toptier_code}/`
- **Method**: GET
- **Documentation**: https://api.usaspending.gov/docs/endpoints
- **Purpose**: Return overview information for a given federal agency by top-tier agency code
- **Corresponding Query Builder**: `src/usaspending/queries/agency_query.py`
- **Note**: The repository markdown contract for `/api/v2/references/agency/{id}/` documents a different endpoint keyed by `agency_id` that returns a nested `results` object. `AgencyQuery` does not use that endpoint.

### Agency Award Summary

- **Endpoint**: `/api/v2/agency/{toptier_code}/awards/`
- **Method**: GET
- **Documentation**: https://api.usaspending.gov/docs/endpoints
- **Purpose**: Return transaction-count and obligation summary information for a given top-tier agency
- **Corresponding Query Builder**: `src/usaspending/queries/agency_award_summary.py`

### Agency Subagencies

- **Endpoint**: `/api/v2/agency/{toptier_code}/sub_agency/`
- **Method**: GET
- **Documentation**: https://api.usaspending.gov/docs/endpoints
- **Purpose**: Return sub-agencies and offices for a given top-tier agency
- **Corresponding Query Builder**: `src/usaspending/queries/sub_agency_query.py`

### Funding Agencies Search

- **Endpoint**: `/api/v2/autocomplete/funding_agency_office/`
- **Method**: POST
- **Documentation**: https://raw.githubusercontent.com/fedspendingtransparency/usaspending-api/refs/heads/master/usaspending_api/api_contracts/contracts/v2/autocomplete/funding_agency_office.md
- **Purpose**: Searches funding agencies, sub-agencies, and offices with names matching the search text.
- **Corresponding Query Builder**: `src/usaspending/queries/agencies_search.py`
- **Note**: The live API returns `results` as an object with `toptier_agency`, `subtier_agency`, and `office` arrays.

### Awarding Agencies Search

- **Endpoint**: `/api/v2/autocomplete/awarding_agency_office/`
- **Method**: POST
- **Documentation**: https://raw.githubusercontent.com/fedspendingtransparency/usaspending-api/refs/heads/master/usaspending_api/api_contracts/contracts/v2/autocomplete/awarding_agency_office.md
- **Purpose**: Searches awarding agencies, sub-agencies, and offices with names matching the search text.
- **Corresponding Query Builder**: `src/usaspending/queries/agencies_search.py`
- **Note**: The live API returns `results` as an object with `toptier_agency`, `subtier_agency`, and `office` arrays.

### TAS Filter Tree - Agencies

- **Endpoint**: `/api/v2/references/filter_tree/tas/`
- **Method**: GET
- **Documentation**: https://raw.githubusercontent.com/fedspendingtransparency/usaspending-api/refs/heads/master/usaspending_api/api_contracts/contracts/v2/references/filter_tree/tas.md
- **Purpose**: List agencies that have at least one Treasury Account Symbol (TAS)
- **Corresponding Resource**: `src/usaspending/resources/tas_resource.py`

### TAS Filter Tree - Federal Accounts

- **Endpoint**: `/api/v2/references/filter_tree/tas/{toptier_code}/`
- **Method**: GET
- **Documentation**: https://raw.githubusercontent.com/fedspendingtransparency/usaspending-api/refs/heads/master/usaspending_api/api_contracts/contracts/v2/references/filter_tree/tas/agency.md
- **Purpose**: List federal accounts under a given top-tier agency that have Treasury Account Symbols
- **Corresponding Query Builder**: `src/usaspending/queries/federal_accounts_query.py`

### TAS Filter Tree - TAS Codes

- **Endpoint**: `/api/v2/references/filter_tree/tas/{toptier_code}/{federal_account}/`
- **Method**: GET
- **Documentation**: https://raw.githubusercontent.com/fedspendingtransparency/usaspending-api/refs/heads/master/usaspending_api/api_contracts/contracts/v2/references/filter_tree/tas/agency/federal_account.md
- **Purpose**: List Treasury Account Symbols (TAS) under a given federal account
- **Corresponding Query Builder**: `src/usaspending/queries/tas_codes_query.py`

### Download Award Data

- **Endpoints**:
  - `/api/v2/download/contract/`
  - `/api/v2/download/assistance/`
  - `/api/v2/download/idv/`
- **Method**: POST
- **Documentation**:
  - https://raw.githubusercontent.com/fedspendingtransparency/usaspending-api/refs/heads/master/usaspending_api/api_contracts/contracts/v2/download/contract.md
  - https://raw.githubusercontent.com/fedspendingtransparency/usaspending-api/refs/heads/master/usaspending_api/api_contracts/contracts/v2/download/assistance.md
  - https://raw.githubusercontent.com/fedspendingtransparency/usaspending-api/refs/heads/master/usaspending_api/api_contracts/contracts/v2/download/idv.md
- **Purpose**: Create a download job for contract, assistance, or IDV award data and return generated file metadata plus a status URL.
- **Corresponding Resource**: `src/usaspending/resources/download_resource.py`
- **Key Parameters**:
  - `award_id`: (required, string) The internal generated award ID from USASpending.gov
  - `file_format`: (optional, enum[string]) The format of the file(s) in the zip archive (`csv`, `tsv`, `pstxt`)
- **Response**: JSON object with the following parameters:
  - `status_url` (required, string): Endpoint used to get the status of a download
  - `file_name` (required, string): Name of the generated zip file
  - `file_url` (required, string): URL for the generated file
  - `download_request` (required, object): Request payload used to generate the download

### Search Download

- **Endpoint**: `/api/v2/download/search/`
- **Method**: POST
- **Documentation**: https://raw.githubusercontent.com/fedspendingtransparency/usaspending-api/refs/heads/master/usaspending_api/api_contracts/contracts/v2/download/search.md
- **Purpose**: Create a download job combining award, transaction, and subaward data matching a set of search filters into a single zip archive.
- **Corresponding Resource**: `src/usaspending/resources/download_resource.py`
- **Key Parameters**:
  - `filters`: (required, object) The standard search filters object (the same one used by `/api/v2/search/spending_by_award/`)
  - `file_format`: (optional, enum[string]) The format of the file(s) in the zip archive (`csv`, `tsv`, `pstxt`)
  - `spending_level`: (optional, array[enum[string]]) Datasets to include: `awards`, `transactions`, `subawards`; defaults to all three
  - `columns`: (optional, array[string]) Specific columns to include; defaults to the full column set
  - `limit`: (optional, number) Maximum number of records to include
- **Response**: JSON object with the same shape as the other download endpoints (`status_url`, `file_name`, `file_url`, `download_request`)
- **Note**: This endpoint's filter validator does not include `object_classes` and silently drops the key. `client.downloads.search()` still forwards the filter unmodified but emits a `UserWarning` when the query carries it.

### Download Status

- **Endpoint**: `/api/v2/download/status`
- **Method**: GET
- **Documentation**: https://raw.githubusercontent.com/fedspendingtransparency/usaspending-api/refs/heads/master/usaspending_api/api_contracts/contracts/v2/download/status.md
- **Purpose**: Gets the current status of a download job.
- **Corresponding Resource**: `src/usaspending/resources/download_resource.py`
- **Key Parameter**: `file_name` (required, string) Taken from the `file_name` field of a download endpoint response.
- **Response**: JSON object with the following parameters:
  - `file_name` (required, string): Name of the generated zip file
  - `message` (required, string, nullable): Human-readable error message if the status is `failed`, otherwise `null`
  - `seconds_elapsed` (required, string, nullable): Time spent generating the file so far, or total generation time once complete
  - `status` (required, enum[string]): Current state of the CSV generation request (`failed`, `finished`, `ready`, `running`)
  - `total_columns` (required, number, nullable): Number of columns in the CSV, or `null` if not finished
  - `total_rows` (required, number, nullable): Number of rows in the CSV, or `null` if not finished
  - `total_size` (required, number, nullable): Estimated CSV size in kilobytes, or `null` if not finished
  - `file_url` (required, string): URL for the generated file
