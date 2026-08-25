import pytest

from tests.mocks.response_builder import ResponseBuilder
from tests.model_contracts import (
    TRANSACTION_FIELDS,
    compare_fields,
    expected_date,
    expected_money,
)
from usaspending.models.transaction import Transaction


class TestTransaction:
    @pytest.fixture
    def transaction_data(self, load_fixture):
        return load_fixture("awards/transactions.json")["results"][0]

    @pytest.fixture
    def transaction(self, transaction_data):
        return Transaction(transaction_data)

    @pytest.fixture
    def all_transaction_data(self, load_fixture):
        return load_fixture("awards/transactions.json")["results"]

    def test_id(self, transaction, transaction_data):
        assert transaction.id == transaction_data["id"]

    def test_type(self, transaction, transaction_data):
        assert transaction.type == transaction_data["type"]

    def test_type_description(self, transaction, transaction_data):
        assert transaction.type_description == transaction_data["type_description"]

    def test_action_date_parsing(self, transaction, transaction_data):
        assert transaction.action_date == expected_date(transaction_data["action_date"])

    def test_action_date_invalid_format(self):
        invalid_data = {"action_date": "invalid-date"}
        transaction = Transaction(invalid_data)
        assert transaction.action_date is None

    def test_action_date_none(self):
        no_date_data = {}
        transaction = Transaction(no_date_data)
        assert transaction.action_date is None

    def test_action_type(self, transaction, transaction_data):
        assert transaction.action_type == transaction_data["action_type"]

    def test_action_type_description(self, transaction, transaction_data):
        assert transaction.action_type_description == transaction_data["action_type_description"]

    def test_modification_number(self, transaction, transaction_data):
        assert transaction.modification_number == transaction_data["modification_number"]

    def test_award_description_sentence_case(self, transaction, transaction_data):
        assert transaction.award_description
        assert (
            transaction.award_description.casefold() == transaction_data["description"].casefold()
        )

    def test_federal_action_obligation(self, transaction, transaction_data):
        assert transaction.federal_action_obligation == expected_money(
            transaction_data["federal_action_obligation"]
        )

    def test_face_value_loan_guarantee(self, transaction, transaction_data):
        assert transaction.face_value_loan_guarantee == expected_money(
            transaction_data["face_value_loan_guarantee"]
        )

    def test_original_loan_subsidy_cost(self, transaction, transaction_data):
        assert transaction.original_loan_subsidy_cost == expected_money(
            transaction_data["original_loan_subsidy_cost"]
        )

    def test_cfda_number(self, transaction, transaction_data):
        assert transaction.cfda_number == transaction_data.get("cfda_number")

    def test_amt_federal_action_obligation(self, transaction):
        assert transaction.amt == transaction.federal_action_obligation

    def test_amt_face_value_loan_guarantee(self):
        data = {
            "federal_action_obligation": None,
            "face_value_loan_guarantee": 500000.0,
            "original_loan_subsidy_cost": None,
        }
        transaction = Transaction(data)
        assert transaction.amt == expected_money(data["face_value_loan_guarantee"])

    def test_amt_original_loan_subsidy_cost(self):
        data = {
            "federal_action_obligation": None,
            "face_value_loan_guarantee": None,
            "original_loan_subsidy_cost": 250000.0,
        }
        transaction = Transaction(data)
        assert transaction.amt == expected_money(data["original_loan_subsidy_cost"])

    def test_amt_zero_obligation_falls_through_to_loan_value(self):
        # Loan rows report a zero obligation with the real figure in the loan
        # fields, so a zero falls through to them (verified against live rows).
        data = {
            "federal_action_obligation": 0,
            "face_value_loan_guarantee": 500000.0,
            "original_loan_subsidy_cost": None,
        }
        transaction = Transaction(data)
        assert transaction.amt == expected_money(data["face_value_loan_guarantee"])

    def test_amt_all_zero_is_zero_not_none(self):
        # Zero-preservation: when every present amount is zero, amt reports
        # Decimal("0.00") rather than the None the old or-chain produced.
        data = {
            "federal_action_obligation": 0,
            "face_value_loan_guarantee": 0.0,
            "original_loan_subsidy_cost": None,
        }
        transaction = Transaction(data)
        assert transaction.amt == expected_money(data["federal_action_obligation"])
        assert transaction.amt is not None

    def test_amt_negative_federal_action_obligation(self):
        data = {
            "federal_action_obligation": -25000.0,
            "face_value_loan_guarantee": None,
            "original_loan_subsidy_cost": None,
        }
        transaction = Transaction(data)
        assert transaction.amt == expected_money(data["federal_action_obligation"])

    def test_amt_loan_fallback_when_obligation_key_absent(self):
        data = {
            "face_value_loan_guarantee": 500000.0,
            "original_loan_subsidy_cost": 12500.0,
        }
        transaction = Transaction(data)
        assert transaction.amt == expected_money(data["face_value_loan_guarantee"])

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
        assert transaction.amt == expected_money(data["federal_action_obligation"])

    def test_repr(self, transaction):
        expected = f"<Txn {transaction.id} {transaction.action_date} {transaction.amt:.2f}>"
        assert repr(transaction) == expected

    def test_repr_no_date(self):
        data = {"id": "test-id", "federal_action_obligation": 100000.0}
        transaction = Transaction(data)
        expected = "<Txn test-id ? 100000.00>"
        assert repr(transaction) == expected

    def test_all_fixture_transactions(self, all_transaction_data):
        for index, tx_data in enumerate(all_transaction_data):
            transaction = Transaction(tx_data)

            compare_fields(f"transaction[{index}]", transaction, TRANSACTION_FIELDS)
            assert transaction.type == tx_data.get("type")
            assert transaction.action_type_description == tx_data.get("action_type_description")
            assert transaction.cfda_number == tx_data.get("cfda_number")
            assert transaction.award_description.casefold() == tx_data["description"].casefold()
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

    def test_with_mock_client_fixture_response(self, mock_usa_client, all_transaction_data):
        mock_usa_client.set_fixture_response("/transactions/", "awards/transactions")

        response = mock_usa_client._make_request("POST", "/transactions/", {})
        transactions = [Transaction(tx_data) for tx_data in response["results"]]

        assert len(transactions) == len(all_transaction_data)
        for index, transaction in enumerate(transactions):
            compare_fields(f"mock transaction[{index}]", transaction, TRANSACTION_FIELDS)

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

        assert transaction.id == tx_data["id"]
        assert transaction.type == tx_data["type"]
        assert transaction.action_date == expected_date(tx_data["action_date"])
        assert transaction.amt == expected_money(tx_data["federal_action_obligation"])

    def test_since_filters_by_action_date(self, mock_usa_client, all_transaction_data):
        def transform(data):
            data["page_metadata"]["hasNext"] = False
            return data

        mock_usa_client.set_fixture_response(
            "/transactions/", "awards/transactions", transform=transform
        )

        boundary_text = "2025-06-10"
        boundary = expected_date(boundary_text)
        results = list(mock_usa_client.transactions.award_id("CONT_AWD_123").since(boundary_text))

        expected = [
            expected_date(tx_data["action_date"])
            for tx_data in all_transaction_data
            if expected_date(tx_data["action_date"]) >= boundary
        ]
        assert [tx.action_date for tx in results] == expected

    def test_until_filters_by_action_date(self, mock_usa_client, all_transaction_data):
        def transform(data):
            data["page_metadata"]["hasNext"] = False
            return data

        mock_usa_client.set_fixture_response(
            "/transactions/", "awards/transactions", transform=transform
        )

        boundary_text = "2025-06-10"
        boundary = expected_date(boundary_text)
        results = list(mock_usa_client.transactions.award_id("CONT_AWD_123").until(boundary_text))

        expected = [
            expected_date(tx_data["action_date"])
            for tx_data in all_transaction_data
            if expected_date(tx_data["action_date"]) <= boundary
        ]
        assert [tx.action_date for tx in results] == expected


class TestTransactionIdentity:
    """Transactions compare by identity, not as equal-by-default records.

    Transaction was declared ``@dataclass`` with no fields, which generated an
    ``__eq__`` comparing empty tuples. Every Transaction therefore compared
    equal to every other one regardless of its data, and ``__hash__`` was set
    to None, making instances unhashable.
    """

    def test_transactions_with_different_data_are_not_equal(self):
        """Two transactions holding different records must not compare equal."""
        first = Transaction({"id": "1", "federal_action_obligation": 100})
        second = Transaction({"id": "2", "federal_action_obligation": 999})

        assert first != second

    def test_transaction_equals_itself(self):
        """Identity comparison still holds for the same instance."""
        transaction = Transaction({"id": "1"})

        assert transaction == transaction

    def test_transactions_are_hashable(self):
        """Instances can go in sets and dict keys."""
        first = Transaction({"id": "1"})
        second = Transaction({"id": "2"})

        assert len({first, second}) == 2
