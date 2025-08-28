"""Tests for SubTierAgency model."""

from usaspending.models.subtier_agency import SubTierAgency
from usaspending.utils.formatter import contracts_titlecase


class TestSubTierAgency:
    """Test SubTierAgency model functionality."""

    def test_basic_properties(self, mock_usa_client):
        """Test basic SubTierAgency properties."""
        data = {
            "name": "National Aeronautics and Space Administration",
            "abbreviation": "NASA",
            "code": "80HQTR",
            "total_obligations": 17275121376.15,
            "transaction_count": 29818,
            "new_award_count": 5465
        }
        
        agency = SubTierAgency(data, mock_usa_client)
        
        assert agency.name == "National Aeronautics and Space Administration"
        assert agency.abbreviation == "NASA"
        assert agency.code == "80HQTR"
        assert agency.total_obligations == 17275121376.15
        assert agency.transaction_count == 29818
        assert agency.new_award_count == 5465

    def test_offices_property(self, mock_usa_client):
        """Test offices property returns SubTierAgency objects."""
        data = {
            "name": "NASA",
            "abbreviation": "NASA",
            "total_obligations": 17275121376.15,
            "transaction_count": 29818,
            "new_award_count": 5465,
            "children": [
                {
                    "code": "80JSC0",
                    "name": "NASA JOHNSON SPACE CENTER",
                    "total_obligations": 3938738374.3,
                    "transaction_count": 1899,
                    "new_award_count": 210
                },
                {
                    "code": "80MSFC",
                    "name": "NASA MARSHALL SPACE FLIGHT CENTER",
                    "total_obligations": 3140833781.78,
                    "transaction_count": 1566,
                    "new_award_count": 158
                }
            ]
        }
        
        agency = SubTierAgency(data, mock_usa_client)
        offices = agency.offices
        
        assert len(offices) == 2
        assert all(isinstance(office, SubTierAgency) for office in offices)
        
        # Test first office - names are transformed by contracts_titlecase
        assert offices[0].code == "80JSC0"
        assert offices[0].name == contracts_titlecase("NASA JOHNSON SPACE CENTER")
        assert offices[0].total_obligations == 3938738374.3
        assert offices[0].transaction_count == 1899
        assert offices[0].new_award_count == 210
        
        # Test second office
        assert offices[1].code == "80MSFC"
        assert offices[1].name == contracts_titlecase("NASA MARSHALL SPACE FLIGHT CENTER")
        assert offices[1].total_obligations == 3140833781.78
        assert offices[1].transaction_count == 1566
        assert offices[1].new_award_count == 158

    def test_offices_empty_children(self, mock_usa_client):
        """Test offices property with empty children."""
        data = {
            "name": "Test Agency",
            "children": []
        }
        
        agency = SubTierAgency(data, mock_usa_client)
        offices = agency.offices
        
        assert offices == []

    def test_offices_no_children_key(self, mock_usa_client):
        """Test offices property with no children key."""
        data = {
            "name": "Test Agency"
        }
        
        agency = SubTierAgency(data, mock_usa_client)
        offices = agency.offices
        
        assert offices == []

    def test_offices_invalid_children_data(self, mock_usa_client):
        """Test offices property with invalid children data."""
        data = {
            "name": "Test Agency",
            "children": "invalid"  # Not a list
        }
        
        agency = SubTierAgency(data, mock_usa_client)
        offices = agency.offices
        
        assert offices == []

    def test_string_representation(self, mock_usa_client):
        """Test string representation of SubTierAgency."""
        data = {
            "name": "Test Agency",
            "code": "123"
        }
        
        agency = SubTierAgency(data, mock_usa_client)
        
        assert str(agency) == "<SubTierAgency 123: Test Agency>"
        assert repr(agency) == "<SubTierAgency 123: Test Agency>"

    def test_string_representation_missing_data(self, mock_usa_client):
        """Test string representation with missing data."""
        data = {}
        
        agency = SubTierAgency(data, mock_usa_client)
        
        assert str(agency) == "<SubTierAgency ?: ?>"
        assert repr(agency) == "<SubTierAgency ?: ?>"

    def test_numeric_type_conversion(self, mock_usa_client):
        """Test that numeric fields are properly converted."""
        data = {
            "name": "Test Agency",
            "total_obligations": "12345.67",  # String number
            "transaction_count": "100",       # String number
            "new_award_count": None           # None value
        }
        
        agency = SubTierAgency(data, mock_usa_client)
        
        assert agency.total_obligations == 12345.67
        assert agency.transaction_count == 100
        assert agency.new_award_count is None

    def test_nested_offices_recursive(self, mock_usa_client):
        """Test that nested offices can have their own offices."""
        data = {
            "name": "Parent Agency",
            "children": [
                {
                    "name": "Child Agency",
                    "code": "CHILD1",
                    "children": [
                        {
                            "name": "Grandchild Office",
                            "code": "GRAND1"
                        }
                    ]
                }
            ]
        }
        
        agency = SubTierAgency(data, mock_usa_client)
        offices = agency.offices
        
        assert len(offices) == 1
        child_office = offices[0]
        assert child_office.name == "Child Agency"
        assert child_office.code == "CHILD1"
        
        # Check that the child office has its own offices
        grandchild_offices = child_office.offices
        assert len(grandchild_offices) == 1
        grandchild = grandchild_offices[0]
        assert grandchild.name == "Grandchild Office"
        assert grandchild.code == "GRAND1"