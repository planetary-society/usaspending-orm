"""Download failures must preserve files and respect the destination boundaries."""

import io
import os
import stat
import zipfile
from unittest.mock import Mock

import pytest
import requests

from usaspending import USASpendingClient
from usaspending.download.job import DownloadJob
from usaspending.download.manager import DownloadManager
from usaspending.exceptions import DownloadError
from usaspending.models.download import DownloadState, DownloadStatus

DOWNLOAD_URL = "https://files.usaspending.gov/export.zip"


def binary_response(content=b"complete archive", status=200, headers=None):
    response = requests.Response()
    response.status_code = status
    response.raw = io.BytesIO(content)
    response.headers.update(headers or {})
    response.close = Mock(wraps=response.close)
    return response


def interrupted_chunks(**kwargs):
    yield b"partial archive"
    raise requests.ConnectionError("stream interrupted")


@pytest.mark.parametrize("failure", ["http", "stream", "promotion"])
def test_failed_download_preserves_previous_file(tmp_path, monkeypatch, failure):
    destination = tmp_path / "export.zip"
    destination.write_bytes(b"previous archive")
    destination.chmod(0o640)
    previous_mode = stat.S_IMODE(destination.stat().st_mode)
    response = binary_response(status=404 if failure == "http" else 200)
    if failure == "stream":
        response.iter_content = interrupted_chunks
    if failure == "promotion":
        monkeypatch.setattr(
            "usaspending.client.os.replace", Mock(side_effect=OSError("disk error"))
        )

    with USASpendingClient() as client:
        monkeypatch.setattr(client, "_send_request", Mock(return_value=response))
        with pytest.raises(DownloadError):
            client._download_binary_file(DOWNLOAD_URL, str(destination))

    assert destination.read_bytes() == b"previous archive"
    assert stat.S_IMODE(destination.stat().st_mode) == previous_mode
    assert list(tmp_path.iterdir()) == [destination]
    response.close.assert_called_once()


def test_successful_download_preserves_existing_permissions(tmp_path, requests_mock):
    destination = tmp_path / "export.zip"
    destination.write_bytes(b"previous archive")
    destination.chmod(0o640)
    previous_mode = stat.S_IMODE(destination.stat().st_mode)
    requests_mock.get(DOWNLOAD_URL, content=b"replacement archive")

    with USASpendingClient() as client:
        client._download_binary_file(DOWNLOAD_URL, str(destination))

    assert destination.read_bytes() == b"replacement archive"
    assert stat.S_IMODE(destination.stat().st_mode) == previous_mode
    assert list(tmp_path.iterdir()) == [destination]


def test_new_download_gets_default_file_permissions(tmp_path, requests_mock):
    reference = tmp_path / "reference"
    reference.write_bytes(b"")
    destination = tmp_path / "export.zip"
    requests_mock.get(DOWNLOAD_URL, content=b"archive")

    with USASpendingClient() as client:
        client._download_binary_file(DOWNLOAD_URL, str(destination))

    assert stat.S_IMODE(destination.stat().st_mode) == stat.S_IMODE(reference.stat().st_mode)


@pytest.mark.skipif(os.name == "nt", reason="Creating symlinks requires Windows privileges")
def test_download_replaces_symlink_without_changing_its_target(tmp_path, requests_mock):
    original = tmp_path / "original.zip"
    original.write_bytes(b"original archive")
    destination = tmp_path / "export.zip"
    destination.symlink_to(original)
    requests_mock.get(DOWNLOAD_URL, content=b"new archive")

    with USASpendingClient() as client:
        client._download_binary_file(DOWNLOAD_URL, str(destination))

    assert original.read_bytes() == b"original archive"
    assert not destination.is_symlink()
    assert destination.read_bytes() == b"new archive"


def test_stream_retry_starts_fresh_and_closes_both_responses(tmp_path, monkeypatch, client_config):
    client_config(max_retries=1, retry_delay=0)
    destination = tmp_path / "export.zip"
    destination.write_bytes(b"previous archive")
    interrupted = binary_response()
    interrupted.iter_content = interrupted_chunks
    completed = binary_response()

    with USASpendingClient() as client:
        request = Mock(side_effect=[interrupted, completed])
        monkeypatch.setattr(client._session, "request", request)
        client._download_binary_file(DOWNLOAD_URL, str(destination))
        assert client._request_count == 2

    assert request.call_count == 2
    assert destination.read_bytes() == b"complete archive"
    assert list(tmp_path.iterdir()) == [destination]
    interrupted.close.assert_called_once()
    completed.close.assert_called_once()


@pytest.mark.parametrize("location", ["/next.zip", "https://api.usaspending.gov/next.zip"])
def test_permitted_redirects_are_followed_and_throttled(
    tmp_path, requests_mock, monkeypatch, location
):
    destination = tmp_path / "export.zip"
    target = requests.compat.urljoin(DOWNLOAD_URL, location)
    requests_mock.get(DOWNLOAD_URL, status_code=302, headers={"Location": location})
    requests_mock.get(target, content=b"complete archive")

    with USASpendingClient() as client:
        wait = Mock()
        monkeypatch.setattr(client.rate_limiter, "wait_if_needed", wait)
        client._download_binary_file(DOWNLOAD_URL, str(destination))
        assert wait.call_count == 2
        assert client._request_count == 2

    assert destination.read_bytes() == b"complete archive"
    assert [request.url for request in requests_mock.request_history] == [DOWNLOAD_URL, target]


@pytest.mark.parametrize(
    "location", ["http://files.usaspending.gov/next.zip", "https://unapproved.example/next.zip"]
)
def test_unsafe_redirect_is_rejected_before_contacting_target(tmp_path, requests_mock, location):
    requests_mock.get(DOWNLOAD_URL, status_code=302, headers={"Location": location})
    target = requests_mock.get(location, content=b"must not be downloaded")

    with USASpendingClient() as client, pytest.raises(DownloadError):
        client._download_binary_file(DOWNLOAD_URL, str(tmp_path / "export.zip"))

    assert not target.called
    assert list(tmp_path.iterdir()) == []


def test_redirect_loop_stops_at_session_limit(tmp_path, requests_mock):
    requests_mock.get(DOWNLOAD_URL, status_code=302, headers={"Location": DOWNLOAD_URL})

    with USASpendingClient() as client:
        client._session.max_redirects = 2
        with pytest.raises(DownloadError, match="redirects"):
            client._download_binary_file(DOWNLOAD_URL, str(tmp_path / "export.zip"))

    assert requests_mock.call_count == 3
    assert list(tmp_path.iterdir()) == []


def test_redirect_without_location_closes_response_and_fails(tmp_path, monkeypatch):
    response = binary_response(status=302)
    with USASpendingClient() as client:
        monkeypatch.setattr(client, "_send_request", Mock(return_value=response))
        with pytest.raises(DownloadError, match="redirects"):
            client._download_binary_file(DOWNLOAD_URL, str(tmp_path / "export.zip"))
    response.close.assert_called_once()


@pytest.mark.skipif(os.name == "nt", reason="Creating symlinks requires Windows privileges")
@pytest.mark.parametrize("directory_link", [False, True])
def test_zip_symlink_escape_is_rejected_before_any_file_is_written(tmp_path, directory_link):
    outside = tmp_path / "outside"
    outside.mkdir()
    original = outside / "data.csv"
    original.write_text("original data")
    extract = tmp_path / "extract"
    extract.mkdir()
    link = extract / ("linked" if directory_link else "data.csv")
    link.symlink_to(outside if directory_link else original, target_is_directory=directory_link)
    member = "linked/data.csv" if directory_link else "data.csv"
    archive = tmp_path / "export.zip"
    with zipfile.ZipFile(archive, "w") as output:
        output.writestr("safe.csv", "do not write before validation")
        output.writestr(member, "replacement data")

    with pytest.raises(DownloadError, match="path traversal"):
        DownloadManager(Mock()).unzip_file(str(archive), str(extract))

    assert original.read_text() == "original data"
    assert not (extract / "safe.csv").exists()


@pytest.mark.skipif(os.name == "nt", reason="Creating symlinks requires Windows privileges")
def test_zip_writes_to_exact_validated_path_without_extractall_rewriting(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    extract = tmp_path / "extract"
    (extract / "a").mkdir(parents=True)
    (extract / "a" / "b").symlink_to(outside, target_is_directory=True)
    archive = tmp_path / "export.zip"
    with zipfile.ZipFile(archive, "w") as output:
        output.writestr("a/../b/", "")
        output.writestr("a/../b/data.csv", "correct data")

    files = DownloadManager(Mock()).unzip_file(str(archive), str(extract))

    assert files == [str(extract / "b"), str(extract / "b" / "data.csv")]
    assert (extract / "b" / "data.csv").read_text() == "correct data"
    assert list(outside.iterdir()) == []


@pytest.mark.parametrize(
    "status_data", [{"status": "finished"}, {"status": "finished", "file_url": None}]
)
def test_finished_job_uses_initial_url_when_status_has_no_url(tmp_path, status_data):
    manager = Mock()
    manager.check_status.return_value = DownloadStatus(status_data)
    manager.unzip_file.return_value = [str(tmp_path / "data.csv")]
    job = DownloadJob(manager, "export.zip", DOWNLOAD_URL, {}, str(tmp_path))

    assert job.wait_for_completion() == manager.unzip_file.return_value
    assert manager.download_file.call_args.args[0] == DOWNLOAD_URL
    assert job.state == DownloadState.FINISHED


def test_job_can_resume_after_local_timeout(tmp_path, monkeypatch):
    manager = Mock()
    manager.check_status.side_effect = [
        DownloadStatus({"status": "running"}),
        DownloadStatus({"status": "finished", "file_url": DOWNLOAD_URL}),
    ]
    manager.unzip_file.return_value = [str(tmp_path / "data.csv")]
    job = DownloadJob(manager, "export.zip", DOWNLOAD_URL, {}, str(tmp_path))

    with monkeypatch.context() as context:
        context.setattr("usaspending.download.job.time.monotonic", Mock(side_effect=[0, 2]))
        with pytest.raises(DownloadError) as error:
            job.wait_for_completion(timeout=1)
    assert error.value.status == "timeout"
    assert job.state == DownloadState.RUNNING
    assert job.error_message is None

    assert job.wait_for_completion() == manager.unzip_file.return_value
    assert manager.check_status.call_count == 2
    assert job.state == DownloadState.FINISHED
