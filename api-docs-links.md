# USASpending.gov API Documentation Links

## Core API Documentation
- **API v2 Endpoints**: https://api.usaspending.gov/docs/endpoints

## Key Endpoints Used in This Project

### Award Search
- **Endpoint**: `/api/v2/search/spending_by_award/`
- **Method**: POST
- **Documentation**: https://github.com/fedspendingtransparency/usaspending-api/raw/refs/heads/master/usaspending_api/api_contracts/contracts/v2/search/spending_by_award.md
- **Purpose**: Search for awards by various criteria including agency, geography, time period

### Geographic Spending
- **Endpoint**: `/api/v2/search/spending_by_geography/`
- **Method**: POST
- **Documentation**: https://github.com/fedspendingtransparency/usaspending-api/raw/refs/heads/master/usaspending_api/api_contracts/contracts/v2/search/spending_by_geography.md
- **Purpose**: Get spending totals by geographic location
- **Key Parameters**:
  - `scope`: "place_of_performance" or "recipient_location"
  - `geo_layer`: "state", "district", or "county"
  - `filters`: Geographic and agency filters

### Top Recipients
- **Endpoint**: `/api/v2/search/spending_by_category/recipient/`
- **Method**: POST
- **Documentation**: https://github.com/fedspendingtransparency/usaspending-api/raw/refs/heads/master/usaspending_api/api_contracts/contracts/v2/search/spending_by_category/recipient.md
- **Purpose**: Get top recipients by spending amount

### Award Details
- **Endpoint**: `/api/v2/awards/{award_id}/`
- **Method**: GET
- **Documentation**:https://github.com/fedspendingtransparency/usaspending-api/raw/refs/heads/master/usaspending_api/api_contracts/contracts/v2/awards/award_id.md
- **Purpose**: Get detailed information about a specific award

### Recipient Details
- **Endpoint**: `/api/v2/recipient/{recipient_id}/`
- **Method**: GET
- **Documentation**: https://raw.githubusercontent.com/fedspendingtransparency/usaspending-api/refs/heads/master/usaspending_api/api_contracts/contracts/v2/recipient/recipient_id.md
- **Purpose**: Get detailed recipient information
- **Parameters**: Recipient hash ID in URL path

### Transactions
- **Endpoint**: `/api/v2/transactions/`
- **Method**: POST
- **Documentation**: https://github.com/fedspendingtransparency/usaspending-api/raw/refs/heads/master/usaspending_api/api_contracts/contracts/v2/transactions.md
- **Purpose**: Get transaction details for an award
- **Key Parameters**:
  - `award_id`: Award identifier
  - `page`: Page number
  - `limit`: Results per page (max 5000)
  - `sort`: Sort field
  - `order`: Sort order

  ### Downloads
  - **Endpoints**:
    - `/api/v2/download/contract/`
    - `/api/v2/download/assistance/`
    - `/api/v2/download/idv/`
  - **Method**: POST
  - **Documentation**:
    - https://github.com/fedspendingtransparency/usaspending-api/blob/7e9f7970940f0aa78e0c02941e6373ae81f8519f/usaspending_api/api_contracts/contracts/v2/download/contract.md
    - https://github.com/fedspendingtransparency/usaspending-api/blob/7e9f7970940f0aa78e0c02941e6373ae81f8519f/usaspending_api/api_contracts/contracts/v2/download/assistance.md
    - https://github.com/fedspendingtransparency/usaspending-api/blob/7e9f7970940f0aa78e0c02941e6373ae81f8519f/usaspending_api/api_contracts/contracts/v2/download/idv.md
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
  - **Documentation**: https://github.com/fedspendingtransparency/usaspending-api/blob/7e9f7970940f0aa78e0c02941e6373ae81f8519f/usaspending_api/api_contracts/contracts/v2/download/status.md
  - **Purpose**: Gets the current status of a download job.
  - **Key Parameter**: `file_name` (required, string) Taken from the `file_name` field of a download endpoint response.
  - **Response**: JSON object with the following parameters:
    -`file_name` (required, string) Is the name of the zipfile containing CSVs that will be generated (file_name is -`timestamp` followed by _transactions or _awards).
    -`message` (required, string, nullable) A human readable error message if the status is failed, otherwise it is null.
    -`seconds_elapsed` (required, string, nullable) Is the time taken to genereate the file (if status is finished or failed), or time taken so far (if running).
    -`status` (required, enum[string]) A string representing the current state of the CSV generation request (failed, finished, ready, running).
    -`total_columns` (required, number, nullable) Is the number of columns in the CSV, or null if not finished.
    -`total_rows` (required, number, nullable) Is the number of rows in the CSV, or null if not finished.
    -`total_size` (required, number, nullable) Is the estimated file size of the CSV in kilobytes, or null if not finished.
    -`file_url` (required, string) The URL for the file.
