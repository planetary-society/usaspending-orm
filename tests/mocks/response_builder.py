"""Helper class for building realistic API responses."""

from __future__ import annotations

from typing import Any, Dict, List, Optional


class ResponseBuilder:
    """Build realistic USASpending API responses for testing."""
    
    @staticmethod
    def paginated_response(
        results: List[Dict[str, Any]],
        page: int = 1,
        has_next: bool = False,
        messages: Optional[List[str]] = None,
        page_size: int = 20,
    ) -> Dict[str, Any]:
        """Build a paginated response with metadata.
        
        Args:
            results: List of result items
            page: Current page number
            has_next: Whether there are more pages
            messages: API messages (optional)
            
        Returns:
            Complete API response dict
        """
        response = {
            "limit": page_size,
            "results": results,
            "page_metadata": {
                "page": page,
                "hasNext": has_next,
                # the following values would vary based on actual data
                "last_record_unique_id": 131519463, 
                "last_record_sort_value": "NNX17CD03C"
            },
            "messages": messages or []
        }
            
        return response
    
    @staticmethod
    def award_search_response(
        awards: List[Dict[str, Any]],
        page: int = 1,
        has_next: bool = False
    ) -> Dict[str, Any]:
        """Build an award search response with proper field mapping.
        
        Args:
            awards: List of award data dicts
            page: Current page number  
            has_next: Whether there are more pages
            
        Returns:
            Award search API response
        """
        # Ensure required fields are present
        for award in awards:
            if "Award ID" not in award:
                award["Award ID"] = f"AWARD-{id(award)}"
            if "Recipient Name" not in award:
                award["Recipient Name"] = "Unknown Recipient"
            if "Award Amount" not in award:
                award["Award Amount"] = 0
                
        return ResponseBuilder.paginated_response(awards, page, has_next)
    
    @staticmethod
    def count_response(
        contracts: int = 0,
        grants: int = 0,
        idvs: int = 0,
        loans: int = 0,
        direct_payments: int = 0,
        other: int = 0
    ) -> Dict[str, Any]:
        """Build an award count response.
        
        Args:
            contracts: Number of contract awards
            grants: Number of grant awards
            idvs: Number of IDV awards
            loans: Number of loan awards
            direct_payments: Number of direct payment awards
            other: Number of other awards
            
        Returns:
            Award count API response
        """
        return {
            "results": {
                "contracts": contracts,
                "grants": grants,
                "idvs": idvs,
                "loans": loans,
                "direct_payments": direct_payments,
                "other": other
            },
            "spending_level": "awards",
            "messages": []
        }
    
    @staticmethod
    def transaction_response(
        transactions: List[Dict[str, Any]],
        page: int = 1,
        has_next: bool = False
    ) -> Dict[str, Any]:
        """Build a transaction search response.
        
        Args:
            transactions: List of transaction data
            page: Current page number
            has_next: Whether there are more pages
            
        Returns:
            Transaction API response
        """
        return ResponseBuilder.paginated_response(transactions, page, has_next)
    
    @staticmethod
    def error_response(
        status_code: int,
        detail: Optional[str] = None,
        error: Optional[str] = None
    ) -> Dict[str, Any]:
        """Build an error response.
        
        Args:
            status_code: HTTP status code
            detail: Error detail message (for 400 errors)
            error: General error message
            
        Returns:
            Error response dict
        """
        if detail:
            return {"detail": detail}
        elif error:
            return {"error": error}
        else:
            return {"error": f"HTTP {status_code} Error"}
    
    @staticmethod
    def award_detail_response(
        award_id: str,
        recipient_name: str = "Test Recipient",
        total_obligations: float = 1000000.0,
        award_type: str = "A",
        awarding_agency: str = "Test Agency"
    ) -> Dict[str, Any]:
        """Build an award detail response.
        
        Args:
            award_id: Unique award identifier
            recipient_name: Name of recipient
            total_obligations: Total award amount
            award_type: Type code of award
            awarding_agency: Name of awarding agency
            
        Returns:
            Award detail API response
        """
        return {
            "generated_unique_award_id": award_id,
            "recipient": {
                "recipient_name": recipient_name,
                "business_types": [],
                "location": {
                    "country_name": "UNITED STATES",
                    "state_code": "CA",
                    "city_name": "SAN FRANCISCO"
                }
            },
            "total_obligation": total_obligations,
            "total_outlay": total_obligations * 0.8,  # 80% outlays
            "award_type": award_type,
            "category": "contract" if award_type in ["A", "B", "C", "D"] else "grant",
            "type_description": "Contract" if award_type in ["A", "B", "C", "D"] else "Grant",
            "awarding_agency": {
                "toptier_agency": {
                    "name": awarding_agency
                }
            },
            "place_of_performance": {
                "country_name": "UNITED STATES", 
                "state_code": "CA",
                "city_name": "SAN FRANCISCO"
            }
        }