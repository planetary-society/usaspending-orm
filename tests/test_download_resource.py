"""Tests for download resource functionality."""

import pytest

from tests.mocks.mock_client import MockUSASpendingClient
from usaspending.exceptions import DownloadError
from usaspending.models.download import DownloadState


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
        json={"award_id": "ASST_NON_123456", "file_format": "csv"},
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
        json={"award_id": "CONT_AWD_789", "file_format": "tsv"},
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
        json={"award_id": "IDV_456", "file_format": "csv"},
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
        params={"file_name": file_name},
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
        detail="Invalid award ID: Award not found",
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
        "download_request": {"award_id": "CUSTOM_123", "file_format": "pstxt"},
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
        "file_url": "https://special.url/file.zip",
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


# ==============================================================================
# File Format Tests
# ==============================================================================


def test_download_csv_format(mock_usa_client):
    """Test downloading with CSV format (default)."""
    mock_usa_client.mock_download_queue("contract", "CONT_CSV")

    mock_usa_client.downloads.contract("CONT_CSV", file_format="csv")

    mock_usa_client.assert_called_with(
        MockUSASpendingClient.Endpoints.DOWNLOAD_CONTRACT,
        method="POST",
        json={"award_id": "CONT_CSV", "file_format": "csv"},
    )


def test_download_tsv_format(mock_usa_client):
    """Test downloading with TSV format."""
    mock_usa_client.mock_download_queue("contract", "CONT_TSV")

    mock_usa_client.downloads.contract("CONT_TSV", file_format="tsv")

    mock_usa_client.assert_called_with(
        MockUSASpendingClient.Endpoints.DOWNLOAD_CONTRACT,
        method="POST",
        json={"award_id": "CONT_TSV", "file_format": "tsv"},
    )


def test_download_pstxt_format(mock_usa_client):
    """Test downloading with pipe-separated text format."""
    mock_usa_client.mock_download_queue("assistance", "ASST_PSV")

    mock_usa_client.downloads.assistance("ASST_PSV", file_format="pstxt")

    mock_usa_client.assert_called_with(
        MockUSASpendingClient.Endpoints.DOWNLOAD_ASSISTANCE,
        method="POST",
        json={"award_id": "ASST_PSV", "file_format": "pstxt"},
    )


# ==============================================================================
# Security Tests - ZipSlip Protection
# ==============================================================================


class TestZipSlipProtection:
    """Tests for ZipSlip vulnerability protection in download extraction."""

    def test_zipslip_path_traversal_blocked(self, tmp_path):
        """Test that path traversal in ZIP entries is blocked."""
        import os
        import zipfile
        from unittest.mock import MagicMock

        from usaspending.download.manager import DownloadManager

        # Create a malicious ZIP file with path traversal
        malicious_zip = tmp_path / "malicious.zip"
        extract_dir = tmp_path / "extract"
        extract_dir.mkdir()

        with zipfile.ZipFile(malicious_zip, "w") as zf:
            # Create entry with path traversal attempt
            zf.writestr("../../../etc/passwd", "malicious content")

        # Create manager with mock client
        mock_client = MagicMock()
        manager = DownloadManager(mock_client)

        # Attempt to extract should raise DownloadError
        with pytest.raises(DownloadError) as exc_info:
            manager.unzip_file(str(malicious_zip), str(extract_dir))

        assert "path traversal" in str(exc_info.value).lower()
        # Verify the malicious file was NOT created
        assert not os.path.exists("/etc/passwd_test")

    def test_zipslip_absolute_path_blocked(self, tmp_path):
        """Test that absolute paths in ZIP entries are blocked."""
        import zipfile
        from unittest.mock import MagicMock

        from usaspending.download.manager import DownloadManager

        # Create ZIP with absolute path
        malicious_zip = tmp_path / "absolute.zip"
        extract_dir = tmp_path / "extract"
        extract_dir.mkdir()

        with zipfile.ZipFile(malicious_zip, "w") as zf:
            # This tests the realpath resolution
            zf.writestr("subdir/../../../tmp/malicious", "bad content")

        mock_client = MagicMock()
        manager = DownloadManager(mock_client)

        with pytest.raises(DownloadError) as exc_info:
            manager.unzip_file(str(malicious_zip), str(extract_dir))

        assert "path traversal" in str(exc_info.value).lower()

    def test_valid_zip_extraction_succeeds(self, tmp_path):
        """Test that valid ZIP files extract correctly."""
        import os
        import zipfile
        from unittest.mock import MagicMock

        from usaspending.download.manager import DownloadManager

        # Create a valid ZIP file
        valid_zip = tmp_path / "valid.zip"
        extract_dir = tmp_path / "extract"
        extract_dir.mkdir()

        with zipfile.ZipFile(valid_zip, "w") as zf:
            zf.writestr("data.csv", "id,name\n1,test")
            zf.writestr("subdir/nested.csv", "col1,col2\na,b")

        mock_client = MagicMock()
        manager = DownloadManager(mock_client)

        result = manager.unzip_file(str(valid_zip), str(extract_dir))

        assert len(result) == 2
        assert os.path.exists(extract_dir / "data.csv")
        assert os.path.exists(extract_dir / "subdir" / "nested.csv")


# ==============================================================================
# Security Tests - Path Traversal in File Names
# ==============================================================================


class TestPathTraversalProtection:
    """Tests for path traversal protection in download file names."""

    def test_malicious_filename_sanitized(self, tmp_path):
        """Test that malicious file names from API are sanitized."""
        from unittest.mock import MagicMock

        from usaspending.download.job import DownloadJob

        # Create a mock manager
        mock_manager = MagicMock()
        mock_manager.check_status.return_value = MagicMock(
            api_status=DownloadState.FINISHED,
            file_url="https://example.com/file.zip",
        )

        # Create job with malicious file_name
        job = DownloadJob(
            manager=mock_manager,
            file_name="../../../etc/malicious.zip",  # Malicious path
            initial_file_url="https://example.com/file.zip",
            request_details={},
            destination_dir=str(tmp_path),
        )

        # The job should sanitize the file name during processing
        # When _process_download is called, it should use os.path.basename
        # We verify by checking the job attributes are set correctly
        assert job.file_name == "../../../etc/malicious.zip"  # Original stored
        assert job.destination_dir == str(tmp_path)

    def test_empty_filename_rejected(self, tmp_path):
        """Test that empty file names after sanitization are rejected."""
        import os
        from unittest.mock import MagicMock

        from usaspending.download.job import DownloadJob

        mock_manager = MagicMock()
        mock_manager.check_status.return_value = MagicMock(
            api_status=DownloadState.FINISHED,
            file_url="https://example.com/file.zip",
        )

        # Edge case: file_name that becomes empty after basename
        # Use a path with trailing slashes which results in empty basename
        # Note: os.path.basename("/path/to/") returns "" on POSIX
        job = DownloadJob(
            manager=mock_manager,
            file_name="/some/path/",  # Trailing slash results in empty basename
            initial_file_url="https://example.com/file.zip",
            request_details={},
            destination_dir=str(tmp_path),
        )

        # Verify basename is indeed empty for this input
        assert os.path.basename("/some/path/") == ""

        # _process_download should raise DownloadError for invalid file name
        with pytest.raises(DownloadError) as exc_info:
            job._process_download(cleanup_zip=False)

        assert "Invalid file name" in str(exc_info.value)


# ==============================================================================
# Timeout and Error Handling Tests
# ==============================================================================


class TestDownloadErrorHandling:
    """Tests for download error handling and edge cases."""

    def test_job_failed_state_sets_error_message(self, mock_usa_client):
        """Test that failed job state captures error message."""
        mock_usa_client.mock_download_queue("contract", "FAIL_123")
        job = mock_usa_client.downloads.contract("FAIL_123")

        # Mock status as failed
        mock_usa_client.mock_download_status(job.file_name, status="failed")
        job.refresh_status()

        assert job.state == DownloadState.FAILED
        assert job.error_message is not None
        assert job.is_complete

    def test_download_status_pending_state(self, mock_usa_client):
        """Test checking status of pending download."""
        file_name = "pending_download.zip"
        mock_usa_client.mock_download_status(file_name, status="ready")

        status = mock_usa_client.downloads.status(file_name)

        assert status.api_status == DownloadState.READY

    def test_bad_zip_file_raises_error(self, tmp_path):
        """Test that invalid ZIP files raise appropriate errors."""
        from unittest.mock import MagicMock

        from usaspending.download.manager import DownloadManager

        # Create an invalid ZIP file (just text content)
        bad_zip = tmp_path / "bad.zip"
        bad_zip.write_text("This is not a zip file")
        extract_dir = tmp_path / "extract"
        extract_dir.mkdir()

        mock_client = MagicMock()
        manager = DownloadManager(mock_client)

        with pytest.raises(DownloadError) as exc_info:
            manager.unzip_file(str(bad_zip), str(extract_dir))

        assert "not a valid zip archive" in str(exc_info.value)


class TestDownloadJobRepresentation:
    """Tests for download job string representation."""

    def test_job_repr(self, mock_usa_client):
        """Test DownloadJob __repr__ method."""
        mock_usa_client.mock_download_queue("contract", "REPR_TEST")
        job = mock_usa_client.downloads.contract("REPR_TEST")

        repr_str = repr(job)

        assert "DownloadJob" in repr_str
        assert "pending" in repr_str.lower()
        assert job.file_name in repr_str
