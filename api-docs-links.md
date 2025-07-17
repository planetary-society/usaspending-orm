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