from usaspending.client_session import get_usaspending_client, USASpendingClient
from usaspending.data_types.recipient import Recipient
from usaspending.data_types.award import Award
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from congress.member import Member
from congress.client_session import get_congress_client, CongressAPIClient
from congress.congress import Congress
from us.states import lookup as state_lookup
import logging
import csv
import os

logger = logging.getLogger(__name__)

class Locale():
    def __init__(self, state_code: str, district: Optional[str] = None):
        state = state_lookup(state_code)
        self.state_name: str = state.name
        self.state_code: str = state.abbr
        self.state_capital: str = state.capital
        self.fips: Optional[str] = state.fips
        self.district: Optional[str] = district
        self.congress: Congress = Congress()
        self.client: USASpendingClient = get_usaspending_client() # load USASpendingAPI session client

    def transactions(self):
        raise NotImplementedError
    
    @property
    def senators(self) -> list["Member"]:
        """ Returns list of senators for the given state """
        members = self._members_of_congress
        senators = []
        for member in members:
            if member.is_senate:
                senators.append(member)
        return senators
    
    @property
    def representatives(self) -> list["Member"]:
        """ Returns a list of all House Representatives for the given state """
        members = self._members_of_congress
        representatives = []
        for member in members:
            if member.is_house:
                representatives.append(member)
        return representatives
    
    @property
    def representative(self) -> Optional["Member"]:
        """ Returns the current house member if self.district is set """
        if self.district:
            members = self._members_of_congress
            for member in members:
                if member.district == self.district:
                    return member
        if self.at_large_state:
            if len(self.representatives) > 0:
                return self.representatives[0]
        if self.district:
            logger.warning(f"No House member fround for {self.state_code}-{self.district}.")
        return None
    
    @cached_property
    def state_congressional_districts(self) -> list[str]:
        """
        Returns an array of all 2-digit district numbers in the state.
        Loads from congressional_districts.csv file, which uses generated the 2020 census allocations.
        """
        csv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'congressional_districts.csv')
        
        districts = []
        try:
            with open(csv_path, 'r', newline='', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    if row['State'] == self.state_code:
                        districts.append(row['District'])
        except FileNotFoundError:
            logger.error(f"Congressional districts CSV file not found at {csv_path}. This is required.")
            exit(1)
        
        return sorted(districts)

    @cached_property
    def _members_of_congress(self) -> Optional[list["Member"]]:
        """ Returns a list of current members of """
        from congress.member import Member 
        return self.congress.get_current_members_by_state(self.state_code)
    
    def fiscal_year_spending(self, tas_code: str, fiscal_year: int, sub_account_code: Optional[str]) -> Union[float, None]:
        """ Returns total amount obligated to the locale by a given agency in a given year """
        result = self.client.get_spending_by_locale(state_code=self.state_code, congressional_district=self.district,
                                           tas_code=tas_code, fiscal_year=fiscal_year, sub_account_code=sub_account_code)
        return result.get("aggregated_amount")
    
    @validate_kwargs(USASpendingClient.get_top_recipients_by_locale,exclude=("self","state_code","congressional_district"))
    def top_recipients(self, **kwargs) -> List[Recipient]:
        return self._get_top_recipients(**kwargs)
    
    @validate_kwargs(USASpendingClient.get_top_recipients_by_locale,exclude=("self","state_code","congressional_district","types"))
    def top_contract_recipients(self,**kwargs) -> List[Recipient]:
        """ Returns list of contract award recipients, ordered by total award value in the given fiscal year range """
        return self._get_top_recipients(types="contracts", **kwargs)
    
    @validate_kwargs(USASpendingClient.get_top_recipients_by_locale,exclude=("self","state_code","congressional_district","types"))
    def top_grant_recipients(self, **kwargs) -> List[Recipient]:
        """ Returns list of grant award recipients, ordered by total award value in the given fiscal year range """
        return self._get_top_recipients(types="grants", **kwargs)
    
    @validate_kwargs(USASpendingClient.top_awards_by_locale, exclude=("self", "state_code", "congressional_district"))
    def top_awards(self, **kwargs) -> List[Award]:
        return self._get_top_awards(**kwargs)

    @validate_kwargs(USASpendingClient.top_awards_by_locale, exclude=("self", "state_code", "congressional_district", "types"))
    def top_contract_awards(self, **kwargs) -> List[Award]:
        return self._get_top_awards(types="contracts", **kwargs)

    @validate_kwargs(USASpendingClient.top_awards_by_locale, exclude=("self", "state_code", "congressional_district", "types"))
    def top_grant_awards(self, **kwargs) -> List[Award]:
        return self._get_top_awards(types="grants", **kwargs)

    def _get_top_awards(self, types:str = "all", **kwargs) -> List[Award]:
        results = self.client.top_awards_by_locale(
            state_code=self.state_code,
            congressional_district=self.district,
            types=types,
            **kwargs
        )
        limit = kwargs.get("limit", 25)
        return [Award(r) for r in results][:limit]

    def _get_top_recipients(self, types:str = "all", **kwargs) -> List[Recipient]:
        """ Private helper: returns recipients ordered by value over a given time range """
        results = self.client.get_top_recipients_by_locale(
            state_code=self.state_code,
            congressional_district=self.district,
            types=types,
            **kwargs
        )
        return [Recipient(r) for r in results]

    @property
    def at_large_state(self):
        return (self.state_code in Congress.AT_LARGE_STATES)