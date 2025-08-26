"""Tests for download resource functionality."""

import pytest
from usaspending.models.download import DownloadState
from usaspending.exceptions import DownloadError, APIError
from tests.mocks.mock_client import MockUSASpendingClient


def test_queue_assistance_download(mock_usa_client):
    """Test queuing an assistance download using default fixture."""
    mock_usa_client.mock_download_queue("assistance", "ASST_NON_123456")
    
    job = mock_usa_client.downloads.assistance("ASST_NON_123456")
    
    # Verify job was created with correct file name
    assert job.file_name.startswith("ASSISTANCE_ASST_NON_123456")
    assert job.file_name.endswith(".zip")
    assert job.state == DownloadState.PENDING
    
    # Verify correct endpoint was called
    mock_usa_client.assert_called_with(
        MockUSASpendingClient.Endpoints.DOWNLOAD_ASSISTANCE,
        method="POST",
        json={"award_id": "ASST_NON_123456", "file_format": "csv"}
    )


def test_queue_contract_download(mock_usa_client):
    """Test queuing a contract download."""
    mock_usa_client.mock_download_queue("contract", "CONT_AWD_789")
    
    job = mock_usa_client.downloads.contract("CONT_AWD_789", file_format="tsv")
    
    assert job.file_name.startswith("CONTRACT_CONT_AWD_789")
    assert job.state == DownloadState.PENDING
    
    # Verify correct format was passed
    mock_usa_client.assert_called_with(
        MockUSASpendingClient.Endpoints.DOWNLOAD_CONTRACT,
        method="POST",
        json={"award_id": "CONT_AWD_789", "file_format": "tsv"}
    )


def test_queue_idv_download(mock_usa_client):
    """Test queuing an IDV download."""
    mock_usa_client.mock_download_queue("idv", "IDV_456")
    
    job = mock_usa_client.downloads.idv("IDV_456")
    
    assert job.file_name.startswith("IDV_IDV_456")
    assert job.state == DownloadState.PENDING
    
    mock_usa_client.assert_called_with(
        MockUSASpendingClient.Endpoints.DOWNLOAD_IDV,
        method="POST",
        json={"award_id": "IDV_456", "file_format": "csv"}
    )


def test_download_status_finished(mock_usa_client):
    """Test checking status of finished download."""
    file_name = "test_download.zip"
    mock_usa_client.mock_download_status(file_name, status="finished")
    
    status = mock_usa_client.downloads.status(file_name)
    
    assert status.api_status == DownloadState.FINISHED
    assert status.file_name == file_name
    assert status.total_size_kb is not None
    assert status.total_rows is not None
    assert status.message is None
    
    # Verify correct endpoint was called
    mock_usa_client.assert_called_with(
        MockUSASpendingClient.Endpoints.DOWNLOAD_STATUS,
        method="GET",
        params={"file_name": file_name}
    )


def test_download_status_running(mock_usa_client):
    """Test checking status of running download."""
    file_name = "running_download.zip"
    mock_usa_client.mock_download_status(file_name, status="running")
    
    status = mock_usa_client.downloads.status(file_name)
    
    assert status.api_status == DownloadState.RUNNING
    assert status.total_size_kb is None
    assert status.total_rows is None
    assert status.seconds_elapsed is not None


def test_download_status_failed(mock_usa_client):
    """Test checking status of failed download."""
    file_name = "failed_download.zip"
    mock_usa_client.mock_download_status(file_name, status="failed")
    
    status = mock_usa_client.downloads.status(file_name)
    
    assert status.api_status == DownloadState.FAILED
    assert status.message == "Download failed: Internal server error"
    assert status.file_url is None


def test_download_status_ready(mock_usa_client):
    """Test checking status of ready download."""
    file_name = "ready_download.zip"
    mock_usa_client.mock_download_status(file_name, status="ready")
    
    status = mock_usa_client.downloads.status(file_name)
    
    assert status.api_status == DownloadState.READY
    assert status.seconds_elapsed is None
    assert status.total_size_kb is None


def test_download_error_handling(mock_usa_client):
    """Test error handling with custom response."""
    mock_usa_client.set_error_response(
        MockUSASpendingClient.Endpoints.DOWNLOAD_CONTRACT,
        400,
        detail="Invalid award ID: Award not found"
    )
    
    with pytest.raises(DownloadError) as exc_info:
        mock_usa_client.downloads.contract("INVALID_ID")
    
    assert "Invalid award ID" in str(exc_info.value)


def test_custom_download_response(mock_usa_client):
    """Test using custom response data for download queue."""
    custom_response = {
        "file_name": "custom_file.zip",
        "file_url": "https://example.com/custom.zip",
        "status_url": "https://example.com/status",
        "download_request": {
            "award_id": "CUSTOM_123",
            "file_format": "pstxt"
        }
    }
    
    mock_usa_client.mock_download_queue("assistance", "CUSTOM_123", response_data=custom_response)
    
    job = mock_usa_client.downloads.assistance("CUSTOM_123", file_format="pstxt")
    
    assert job.file_name == "custom_file.zip"
    assert job.request_details["award_id"] == "CUSTOM_123"


def test_custom_status_response(mock_usa_client):
    """Test using custom status response data."""
    custom_status = {
        "status": "finished",
        "file_name": "special.zip",
        "message": None,
        "seconds_elapsed": "42.0",
        "total_size": 999.99,
        "total_columns": 50,
        "total_rows": 1000,
        "file_url": "https://special.url/file.zip"
    }
    
    mock_usa_client.mock_download_status("special.zip", custom_data=custom_status)
    
    status = mock_usa_client.downloads.status("special.zip")
    
    assert status.api_status == DownloadState.FINISHED
    assert status.total_size_kb == 999.99
    assert status.total_rows == 1000
    assert status.total_columns == 50
    assert status.seconds_elapsed == 42.0


def test_download_job_refresh_status(mock_usa_client):
    """Test that download job can refresh its status."""
    # First queue the download
    mock_usa_client.mock_download_queue("contract", "CONT_123")
    job = mock_usa_client.downloads.contract("CONT_123")
    
    assert job.state == DownloadState.PENDING
    
    # Mock status as running
    mock_usa_client.mock_download_status(job.file_name, status="running")
    state = job.refresh_status()
    
    assert state == DownloadState.RUNNING
    assert job.state == DownloadState.RUNNING
    
    # Mock status as finished
    mock_usa_client.mock_download_status(job.file_name, status="finished")
    state = job.refresh_status()
    
    assert state == DownloadState.FINISHED
    assert job.state == DownloadState.FINISHED
    assert job.is_complete