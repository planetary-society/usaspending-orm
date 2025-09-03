import pytest
import json
from datetime import datetime
from pathlib import Path

from src.usaspending.models.transaction import Transaction
from tests.mocks.response_builder import ResponseBuilder


class TestTransaction:
    @pytest.fixture
    def transaction_data(self):
        fixture_path = (
            Path(__file__).parent.parent / "fixtures" / "awards" / "transactions.json"
        )
        with open(fixture_path) as f:
            data = json.load(f)
        return data["results"][0]

    @pytest.fixture
    def transaction(self, transaction_data):
        return Transaction(transaction_data)

    @pytest.fixture
    def all_transaction_data(self):
        fixture_path = (
            Path(__file__).parent.parent / "fixtures" / "awards" / "transactions.json"
        )
        with open(fixture_path) as f:
            data = json.load(f)
        return data["results"]

    def test_id(self, transaction):
        assert transaction.id == "CONT_TX_8000_-NONE-_80GSFC18C0008_P00065_-NONE-_0"

    def test_type(self, transaction):
        assert transaction.type == "D"

    def test_type_description(self, transaction):
        assert transaction.type_description == "DEFINITIVE CONTRACT"

    def test_action_date_parsing(self, transaction):
        assert transaction.action_date == datetime(2025, 6, 23)

    def test_action_date_invalid_format(self):
        invalid_data = {"action_date": "invalid-date"}
        transaction = Transaction(invalid_data)
        assert transaction.action_date is None

    def test_action_date_none(self):
        no_date_data = {}
        transaction = Transaction(no_date_data)
        assert transaction.action_date is None

    def test_action_type(self, transaction):
        assert transaction.action_type == "C"

    def test_action_type_description(self, transaction):
        assert transaction.action_type_description == "FUNDING ONLY ACTION"

    def test_modification_number(self, transaction):
        assert transaction.modification_number == "P00065"

    def test_award_description_sentence_case(self, transaction):
        assert transaction.award_description == "The tandem reconnection...."

    def test_federal_action_obligation(self, transaction):
        assert transaction.federal_action_obligation == 1600000.0

    def test_face_value_loan_guarantee(self, transaction):
        assert transaction.face_value_loan_guarantee == 0.0

    def test_original_loan_subsidy_cost(self, transaction):
        assert transaction.original_loan_subsidy_cost == 0.0

    def test_cfda_number_missing(self, transaction):
        assert transaction.cfda_number is None

    def test_amt_federal_action_obligation(self, transaction):
        assert transaction.amt == 1600000.0

    def test_amt_face_value_loan_guarantee(self):
        data = {
            "federal_action_obligation": None,
            "face_value_loan_guarantee": 500000.0,
            "original_loan_subsidy_cost": None,
        }
        transaction = Transaction(data)
        assert transaction.amt == 500000.0

    def test_amt_original_loan_subsidy_cost(self):
        data = {
            "federal_action_obligation": None,
            "face_value_loan_guarantee": None,
            "original_loan_subsidy_cost": 250000.0,
        }
        transaction = Transaction(data)
        assert transaction.amt == 250000.0

    def test_amt_all_none(self):
        data = {
            "federal_action_obligation": None,
            "face_value_loan_guarantee": None,
            "original_loan_subsidy_cost": None,
        }
        transaction = Transaction(data)
        assert transaction.amt is None

    def test_amt_string_conversion(self):
        data = {
            "federal_action_obligation": "1500000.50",
            "face_value_loan_guarantee": None,
            "original_loan_subsidy_cost": None,
        }
        transaction = Transaction(data)
        assert transaction.amt == 1500000.5

    def test_repr(self, transaction):
        expected = "<Txn CONT_TX_8000_-NONE-_80GSFC18C0008_P00065_-NONE-_0 2025-06-23 00:00:00 1600000.0>"
        assert repr(transaction) == expected

    def test_repr_no_date(self):
        data = {"id": "test-id", "federal_action_obligation": 100000.0}
        transaction = Transaction(data)
        expected = "<Txn test-id None 100000.0>"
        assert repr(transaction) == expected

    def test_all_fixture_transactions(self, all_transaction_data):
        for tx_data in all_transaction_data:
            transaction = Transaction(tx_data)

            assert transaction.id is not None
            assert transaction.type == "D"
            assert transaction.type_description == "DEFINITIVE CONTRACT"
            assert isinstance(transaction.action_date, datetime)
            assert transaction.action_type in ["C", "B"]
            assert transaction.modification_number is not None
            assert transaction.award_description is not None
            assert transaction.federal_action_obligation > 0
            assert transaction.face_value_loan_guarantee == 0.0
            assert transaction.original_loan_subsidy_cost == 0.0
            assert transaction.amt == transaction.federal_action_obligation

    def test_properties_with_missing_data(self):
        empty_data = {}
        transaction = Transaction(empty_data)

        assert transaction.id is None
        assert transaction.type is None
        assert transaction.type_description is None
        assert transaction.action_date is None
        assert transaction.action_type is None
        assert transaction.action_type_description is None
        assert transaction.modification_number is None
        assert transaction.award_description == ""
        assert transaction.federal_action_obligation is None
        assert transaction.face_value_loan_guarantee is None
        assert transaction.original_loan_subsidy_cost is None
        assert transaction.cfda_number is None
        assert transaction.amt is None

    def test_with_mock_client_fixture_response(self, mock_usa_client):
        mock_usa_client.set_fixture_response("/transactions/", "awards/transactions")

        response = mock_usa_client._make_request("POST", "/transactions/", {})
        transactions = [Transaction(tx_data) for tx_data in response["results"]]

        assert len(transactions) == 3
        assert all(tx.type == "D" for tx in transactions)
        assert all(tx.amt > 0 for tx in transactions)

    def test_with_response_builder(self):
        tx_data = {
            "id": "TEST_TX_001",
            "type": "A",
            "type_description": "BPA CALL",
            "action_date": "2024-01-15",
            "action_type": "A",
            "action_type_description": "NEW AWARD",
            "modification_number": "0",
            "description": "Test Contract",
            "federal_action_obligation": 750000.0,
            "face_value_loan_guarantee": 0.0,
            "original_loan_subsidy_cost": 0.0,
        }

        response = ResponseBuilder.transaction_response([tx_data])
        transaction = Transaction(response["results"][0])

        assert transaction.id == "TEST_TX_001"
        assert transaction.type == "A"
        assert transaction.action_date == datetime(2024, 1, 15)
        assert transaction.amt == 750000.0
