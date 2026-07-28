# src/usaspending/resources/download_resource.py

from __future__ import annotations

import warnings
from typing import TYPE_CHECKING

from ..download.job import DownloadJob

# Import the manager and type aliases
from ..download.manager import DownloadManager, FileFormat
from ..exceptions import ValidationError
from ..logging_config import USASpendingLogger
from ..models.download import DownloadStatus, SpendingLevel
from .base_resource import BaseResource

if TYPE_CHECKING:
    from ..client import USASpendingClient
    from ..queries.awards_search import AwardsSearch

logger = USASpendingLogger.get_logger(__name__)


class DownloadResource(BaseResource):
    """Resource for award data download operations."""

    def __init__(self, client: USASpendingClient):
        super().__init__(client)
        self._manager = DownloadManager(client)

    def contract(
        self,
        award_id: str,
        file_format: FileFormat = "csv",
        destination_dir: str | None = None,
    ) -> DownloadJob:
        """
        Queue a download job for contract award data.

        Args:
            award_id: The unique award identifier (e.g., CONT_AWD_...).
            file_format: Format of the file (csv, tsv, pstxt).
            destination_dir: Directory where the file will be saved (defaults to CWD).

        Returns:
            A DownloadJob object. Use job.wait_for_completion() to block until finished.
        """
        return self._manager.queue_download("contract", award_id, file_format, destination_dir)

    def assistance(
        self,
        award_id: str,
        file_format: FileFormat = "csv",
        destination_dir: str | None = None,
    ) -> DownloadJob:
        """
        Queue a download job for assistance award data.

        Args:
            award_id: The unique award identifier (e.g., ASST_NON_...).
            file_format: Format of the file (csv, tsv, pstxt).
            destination_dir: Directory where the file will be saved (defaults to CWD).

        Returns:
            A DownloadJob object. Use job.wait_for_completion() to block until finished.
        """
        return self._manager.queue_download("assistance", award_id, file_format, destination_dir)

    def idv(
        self,
        award_id: str,
        file_format: FileFormat = "csv",
        destination_dir: str | None = None,
    ) -> DownloadJob:
        """
        Queue a download job for IDV (Indefinite Delivery Vehicle) award data.

        Args:
            award_id: The unique award identifier (e.g., IDV_...).
            file_format: Format of the file (csv, tsv, pstxt).
            destination_dir: Directory where the file will be saved (defaults to CWD).

        Returns:
            A DownloadJob object. Use job.wait_for_completion() to block until finished.
        """
        return self._manager.queue_download("idv", award_id, file_format, destination_dir)

    def search(
        self,
        query: AwardsSearch,
        *,
        file_format: FileFormat = "csv",
        spending_level: list[SpendingLevel] | None = None,
        columns: list[str] | None = None,
        limit: int | None = None,
        destination_dir: str | None = None,
    ) -> DownloadJob:
        """
        Queue a download of awards, transactions, and subawards matching a search.

        Builds the request from an existing awards search query, so the same fluent
        filters used for searching can drive a bulk download.

        Args:
            query: An awards search query (e.g. ``client.awards.search().contracts()``)
                whose filters define the download. Subaward searches are accepted as a
                filter source, but which datasets are downloaded is controlled solely by
                the ``spending_level`` argument, not the query type.
            file_format: Format of the file(s) in the zip (csv, tsv, pstxt).
            spending_level: Datasets to include; any of "awards", "transactions", and
                "subawards". When None, the API includes all three.
            columns: Specific columns to include. When None, the API returns its default set.
            limit: Maximum number of records to include. When None, the API default applies.
            destination_dir: Directory where the file will be saved (defaults to CWD).

        Returns:
            A DownloadJob object. Use job.wait_for_completion() to block until finished.

        Raises:
            ValidationError: If ``query`` is not an awards search query.

        Note:
            The ``/download/search/`` endpoint ignores filter keys its validator does
            not recognize, such as ``object_classes``. When the query carries such a
            filter it is still forwarded unmodified, but a ``UserWarning`` is emitted to
            flag that the download will not be narrowed by that filter.

        Example:
            >>> # Download National Aeronautics and Space Administration contracts for FY2024
            >>> query = (
            ...     client.awards.search()
            ...     .contracts()
            ...     .agency("National Aeronautics and Space Administration")
            ...     .fiscal_year(2024)
            ... )
            >>> job = client.downloads.search(query, spending_level=["awards"])
            >>> job.wait_for_completion()
        """
        # Imported here for the runtime type check; annotated under TYPE_CHECKING above.
        from ..queries.awards_search import AwardsSearch

        if not isinstance(query, AwardsSearch):
            raise ValidationError(
                "downloads.search() requires an awards search query, "
                "for example client.awards.search().contracts()."
            )

        filters = query.to_filters_payload()
        if "object_classes" in filters:
            warnings.warn(
                "The 'object_classes' filter is not supported by the "
                "/download/search/ endpoint and will be ignored by the API; "
                "the download will not be narrowed by object class.",
                UserWarning,
                stacklevel=2,
            )

        return self._manager.queue_search_download(
            filters,
            file_format=file_format,
            spending_level=spending_level,
            columns=columns,
            limit=limit,
            destination_dir=destination_dir,
        )

    def status(self, file_name: str) -> DownloadStatus:
        """
        Check the status of a specific download job directly via the API.

        Note: Using DownloadJob.refresh_status() is generally preferred.

        Args:
            file_name: The name of the file returned by the download request.

        Returns:
            The DownloadStatus model representation.
        """
        return self._manager.check_status(file_name)
