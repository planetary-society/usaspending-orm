# src/usaspending/models/download.py

from __future__ import annotations
from typing import Optional, Literal
from enum import Enum

from ..utils.formatter import to_float, to_int
from .base_model import BaseModel

AwardType = Literal["contract", "assistance"]
FileFormat = Literal["csv", "tsv", "pstxt"]

class DownloadState(Enum):
    """Enumeration for download job states."""
    PENDING = "pending" # Custom state before first API check
    READY = "ready"
    RUNNING = "running"
    FINISHED = "finished"
    FAILED = "failed"
    UNKNOWN = "unknown" # Custom state if API returns unexpected value

class DownloadStatus(BaseModel):
    """Represents the status details of a download job returned by the API."""

    @property
    def file_name(self) -> Optional[str]:
        return self.get_value("file_name")

    @property
    def message(self) -> Optional[str]:
        """A human readable error message if the status is failed, otherwise null."""
        return self.get_value("message")

    @property
    def seconds_elapsed(self) -> Optional[float]:
        """Time taken to generate the file or time taken so far."""
        return to_float(self.get_value("seconds_elapsed"))

    @property
    def api_status(self) -> DownloadState:
        """Current state of the request from the API."""
        status_str = self.get_value("status")
        if status_str:
            try:
                return DownloadState(status_str)
            except ValueError:
                return DownloadState.UNKNOWN
        return DownloadState.UNKNOWN

    @property
    def total_columns(self) -> Optional[int]:
        return to_int(self.get_value("total_columns"))

    @property
    def total_rows(self) -> Optional[int]:
        return to_int(self.get_value("total_rows"))

    @property
    def total_size_kb(self) -> Optional[float]:
        """Estimated file size in kilobytes."""
        return to_float(self.get_value("total_size"))

    @property
    def file_url(self) -> Optional[str]:
        """The URL for the file (relative path)."""
        return self.get_value("file_url")

    def __repr__(self) -> str:
        return f"<DownloadStatus status='{self.api_status.value}' file='{self.file_name}'>"