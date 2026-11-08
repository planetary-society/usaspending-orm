"""Read-only contract checks for identifier lookup endpoints."""

import pytest

from usaspending.models.agency import Agency
from usaspending.models.federal_account import FederalAccount

pytestmark = pytest.mark.integration


def test_live_agency_id_resolves_to_its_treasury_code(client, load_fixture):
    funding = load_fixture("awards/award_funding_grant.json")["results"][0]
    agency = Agency({"toptier_agency_id": funding["funding_toptier_agency_id"]}, client)
    assert agency.code == load_fixture("agency.json")["toptier_code"]
    detail = client.agencies.find_by_toptier_code(agency.code)
    assert detail.name == funding["funding_agency_name"]


def test_live_account_resolves_parent_from_tree(client, load_fixture):
    row = load_fixture("tas_federal_accounts.json")["results"][0]
    account = FederalAccount({"id": row["id"]}, client)
    assert account.toptier_code == row["ancestors"][0]
    assert all(tas.federal_account_code == row["id"] for tas in account.tas_codes)
