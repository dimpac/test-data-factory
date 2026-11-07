"""CSV output. Phase 1 stub."""

from __future__ import annotations

from collections.abc import Iterable
import csv
from datetime import date, datetime
from pathlib import Path
from typing import Any


def write_csv(
    path: Path,
    columns: list[str],
    rows: Iterable[dict[str, Any]],
    *,
    batch_size: int = 1000,
) -> int:
    """Write rows in batches without materialising them. Returns the row count.

    Nulls are written as empty fields; dates and timestamps as ISO 8601.
    """
    if batch_size <= 0:
        raise ValueError("batch_size must be positive")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0

    def serialise(value: Any) -> Any:
        if value is None:
            return ""
        if isinstance(value, (datetime, date)):
            return value.isoformat()
        return value

    with path.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(columns)
        batch: list[list[Any]] = []
        for row in rows:
            batch.append([serialise(row.get(column)) for column in columns])
            count += 1
            if len(batch) == batch_size:
                writer.writerows(batch)
                batch.clear()
        if batch:
            writer.writerows(batch)
    return count
