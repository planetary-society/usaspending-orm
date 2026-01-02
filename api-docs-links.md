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
- **Documentation**: https://github.com/fedspendingtransparency/usaspending-api/raw/refs/heads/master/usaspending_api/api_contracts/contracts/v2/search/spending_by_award.md
- **Purpose**: Search for awards by various criteria including agency, geography, time period
- **Corresponding Query Builder**: `src/usaspending/queries/awards_search.py`

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
- **Corresponding Query Builder**: `src/usaspending/queries/recipient_search.py`

### Award Details
- **Endpoint**: `/api/v2/awards/{award_id}/`
- **Method**: GET
- **Documentation**: https://raw.githubusercontent.com/fedspendingtransparency/usaspending-api/refs/heads/master/usaspending_api/api_contracts/contracts/v2/awards/award_id.md
- **Purpose**: Get detailed information about a specific federal award
- **Coresponding Query Builder**: `src/usaspending/queries/award_query.py`

### Recipient Details
- **Endpoint**: `/api/v2/recipient/{recipient_id}/`
- **Method**: GET
- **Documentation**: https://raw.githubusercontent.com/fedspendingtransparency/usaspending-api/refs/heads/master/usaspending_api/api_contracts/contracts/v2/recipient/recipient_id.md
- **Purpose**: Get detailed recipient information
- **Corresponding Query Builder**: `src/usaspending/queries/recipient_query.py`

### Award transactions
- **Endpoint**: `/api/v2/transactions/`
- **Method**: POST
- **Documentation**: https://raw.githubusercontent.com/fedspendingtransparency/usaspending-api/refs/heads/master/usaspending_api/api_contracts/contracts/v2/transactions.md
- **Purpose**: List obligations and modifications for a given award
- **Corresponding Query Builder**: `src/usaspending/queries/transactions_search.py`

### Award funding history
- **Endpoint**: `/api/v2/awards/funding/`
- **Method**: POST
- **Documentation**: https://raw.githubusercontent.com/fedspendingtransparency/usaspending-api/refs/heads/master/usaspending_api/api_contracts/contracts/v2/awards/funding.md
- **Purpose**: Get funding history (obligations and outlays) for a given award
- **Corresponding Query Builder**: `src/usaspending/queries/funding_search.py`

### Subawards
- **Endpoint**: `/api/v2/subawards/`
- **Method**: POST
- **Documentation**: https://raw.githubusercontent.com/fedspendingtransparency/usaspending-api/refs/heads/master/usaspending_api/api_contracts/contracts/v2/subawards.md
- **Purpose**: List subawards for a given award
- **Corresponding Query Builder**: `src/usaspending/queries/subawards_search.py`

### Agency Detail
- **Endpoint**: `/api/v2/references/agency/{id}/`
- **Method**: GET
- **Documentation**: https://raw.githubusercontent.com/fedspendingtransparency/usaspending-api/refs/heads/master/usaspending_api/api_contracts/contracts/v2/references/agency/id.md
- **Purpose**: Return information and spending data for a given federal agency by toptier code ({id}).
- **Corresponding Query Builder**: `src/usaspending/queries/agency_query.py`

### Funding Agencies Search
- **Endpoint**: `/api/v2/autocomplete/funding_agency_office/`
- **Method**: POST
- **Documentation**: https://raw.githubusercontent.com/fedspendingtransparency/usaspending-api/refs/heads/master/usaspending_api/api_contracts/contracts/v2/autocomplete/funding_agency_office.md
- **Purpose**: Searches funding agencies, sub-agencies, and offices with names matching the search text.
- **Corresponding Query Builder**: `src/usaspending/queries/funding_agencies_search.py`

### Awarding Agencies Search
- **Endpoint**: `/api/v2/autocomplete/awarding_agency_office/`
- **Method**: POST
- **Documentation**: https://raw.githubusercontent.com/fedspendingtransparency/usaspending-api/refs/heads/master/usaspending_api/api_contracts/contracts/v2/autocomplete/awarding_agency_office.md
- **Purpose**: Searches awarding agencies, sub-agencies, and offices with names matching the search text.
- **Corresponding Query Builder**: `src/usaspending/queries/awarding_agencies_search.py`

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
- **Purpose**: Creates a new download job for the requested award and returns a link to a zipped file containing contract award data.
- **Key Parameters**:
- `award_id`: (required, string) The internal generated award id from USASpending.gov
- `file_format` (optional, enum[string]) The format of the file(s) in the zip file containing the data (csv, tsv, pstxt) 
- **Response**: JSON object with the following parameters:
- `status_url` (required, string) The endpoint used to get the status of a download.
- `file_name` (required, string) Is the name of the zipfile containing CSVs that will be generated (file_name is timestamp followed by _transactions or _awards).
- `file_url` (required, string) The URL for the file.
- `download_request` (required, object) The JSON object used when processing the download.

### Download Status
- **Endpoint**: `/api/v2/download/status{?file_name}`
- **Method**: GET
- **Documentation**: https://raw.githubusercontent.com/fedspendingtransparency/usaspending-api/refs/heads/master/usaspending_api/api_contracts/contracts/v2/download/status.md
- **Purpose**: Gets the current status of a download job.
- **Key Parameter**: `file_name` (required, string) Taken from the `file_name` field of a download endpoint response.
- **Response**: JSON object with the following parameters:
-`file_name` (required, string) Is the name of the zipfile containing CSVs that will be generated (file_name is timestamp followed by _transactions or _awards).
-`message` (required, string, nullable) A human readable error message if the status is failed, otherwise it is null.
-`seconds_elapsed` (required, string, nullable) Is the time taken to genereate the file (if status is finished or failed), or time taken so far (if running).
-`status` (required, enum[string]) A string representing the current state of the CSV generation request (failed, finished, ready, running).
-`total_columns` (required, number, nullable) Is the number of columns in the CSV, or null if not finished.
-`total_rows` (required, number, nullable) Is the number of rows in the CSV, or null if not finished.
-`total_size` (required, number, nullable) Is the estimated file size of the CSV in kilobytes, or null if not finished.
-`file_url` (required, string) The URL for the file.
