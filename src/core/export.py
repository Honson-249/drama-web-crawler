from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable

from src.core.models import CSV_HEADERS, DramaRecord
from src.core.storage import ensure_directory


def write_records_to_csv(records: Iterable[DramaRecord], output_path: Path) -> Path:
    """Write records to CSV using atomic rename. Supports both iterables and generators.

    The file is written with a .crawling suffix, then renamed to the final
    path upon successful completion to prevent reading partial files.
    """
    ensure_directory(output_path.parent)
    row_count = 0

    # Write to temp file with .crawling suffix first
    crawling_path = Path(str(output_path) + ".crawling")
    with crawling_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_HEADERS)
        writer.writeheader()
        for record in records:
            writer.writerow(record.to_csv_row())
            row_count += 1

    if row_count == 0:
        crawling_path.unlink(missing_ok=True)
        raise ValueError("cannot export an empty record set")

    # Rename to final path atomically
    crawling_path.replace(output_path)
    return output_path


def write_records_to_csv_iter(
    records: Iterable[DramaRecord],
    output_path: Path,
) -> int:
    """Stream write records to CSV. Returns the count of records written.

    The file is written with a .crawling suffix, then renamed to the final
    path upon successful completion to prevent reading partial files.
    """
    ensure_directory(output_path.parent)
    row_count = 0

    # Write to temp file with .crawling suffix first
    crawling_path = Path(str(output_path) + ".crawling")
    with crawling_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_HEADERS)
        writer.writeheader()
        for record in records:
            writer.writerow(record.to_csv_row())
            row_count += 1

    if row_count == 0:
        crawling_path.unlink(missing_ok=True)
        raise ValueError("cannot export an empty record set")

    # Rename to final path atomically
    crawling_path.replace(output_path)
    return row_count
