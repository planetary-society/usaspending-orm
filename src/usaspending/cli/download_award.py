# src/usaspending/cli/download_award.py

import argparse
import sys
import os
from typing import List

# Helper to ensure the package root is in sys.path if running the script directly during development
if __name__ == "__main__":
    # Adjust path relative to the script location (src/usaspending/cli)
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

# Import necessary components from the library
from usaspending.client import USASpending
from usaspending.exceptions import DownloadError
from usaspending.logging_config import USASpendingLogger

def main():
    parser = argparse.ArgumentParser(
        description="Download detailed award data from USASpending.gov.",
        epilog="This CLI tool queues a download job, waits for completion, downloads the zip file, and extracts the contents."
    )

    parser.add_argument("award_id", help="The unique award identifier (e.g., CONT_AWD_..., ASST_NON_...)")
    parser.add_argument("-t", "--type", choices=["contract", "assistance"], required=True, help="The type of the award.")
    parser.add_argument("-o", "--output-dir", help="The directory to save and extract the files (defaults to current directory).")
    parser.add_argument("-f", "--format", choices=["csv", "tsv", "pstxt"], default="csv", help="The format of the files (default: csv).")
    parser.add_argument("--timeout", type=int, default=1800, help="Maximum time in seconds to wait (default: 1800s/30min).")
    parser.add_argument("--poll-interval", type=int, default=30, help="Interval in seconds between status checks (default: 30s).")
    parser.add_argument("--no-cleanup", action="store_true", help="Keep the zip file after extraction.")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose debug logging.")

    args = parser.parse_args()

    # Configure logging
    log_level = "DEBUG" if args.verbose else "INFO"
    USASpendingLogger.configure(level=log_level, debug_mode=args.verbose)
    logger = USASpendingLogger.get_logger("usaspending.cli.download")

    try:
        # Initialize client (assuming default configuration handling)
        client = USASpending()

        logger.info("--- Starting USASpending Award Download CLI ---")
        logger.info(f"Parameters: ID={args.award_id}, Type={args.type}, Format={args.format}")

        # 1. Queue the download
        if args.type == "contract":
            job = client.downloads.contract(args.award_id, file_format=args.format, destination_dir=args.output_dir)
        else:
            job = client.downloads.assistance(args.award_id, file_format=args.format, destination_dir=args.output_dir)
        
        logger.info(f"Job successfully queued. Tracking File: {job.file_name}")

        # 2. Wait for completion (blocking operation)
        extracted_files: List[str] = job.wait_for_completion(
            timeout=args.timeout,
            poll_interval=args.poll_interval,
            cleanup_zip=not args.no_cleanup
        )
        
        logger.info("--- Download and Extraction Complete ---")
        # Determine the final extraction path
        extract_subdir_name = os.path.splitext(job.file_name)[0]
        final_path = os.path.join(job.destination_dir, extract_subdir_name)
        logger.info(f"Data extracted to: {os.path.abspath(final_path)}")
        logger.info(f"Total files extracted: {len(extracted_files)}")

    except DownloadError as e:
        logger.error(f"Download failed. Status: {e.status}. Message: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.warning("Download interrupted by user.")
        sys.exit(1)
    except Exception as e:
        logger.exception(f"An unexpected error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()