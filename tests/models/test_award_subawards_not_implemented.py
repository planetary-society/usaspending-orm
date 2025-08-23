"""Tests for Award types that don't support subawards."""

from __future__ import annotations

import pytest

from usaspending.models.award import Award
from usaspending.models.idv import IDV
from usaspending.models.loan import Loan


class TestAwardSubawardsNotImplemented:
    """Test that award types without subawards raise NotImplementedError."""

    def test_base_award_subawards_raises_not_implemented(self, mock_usa_client):
        """Test that base Award.subawards raises NotImplementedError."""
        award_data = {
            "generated_unique_award_id": "CONT_AWD_123_456",
            "Award ID": "123456",
        }
        award = Award(award_data, mock_usa_client)
        
        with pytest.raises(NotImplementedError):
            award.subawards

    def test_idv_subawards_raises_not_implemented(self, mock_usa_client):
        """Test that IDV.subawards raises NotImplementedError."""
        idv_data = {
            "generated_unique_award_id": "CONT_IDV_123_456",
            "Award ID": "123456",
            "piid": "123456",
        }
        idv = IDV(idv_data, mock_usa_client)
        
        with pytest.raises(NotImplementedError):
            idv.subawards

    def test_loan_subawards_raises_not_implemented(self, mock_usa_client):
        """Test that Loan.subawards raises NotImplementedError."""
        loan_data = {
            "generated_unique_award_id": "ASST_NON_123_456",
            "Award ID": "123456",
        }
        loan = Loan(loan_data, mock_usa_client)
        
        with pytest.raises(NotImplementedError):
            loan.subawards