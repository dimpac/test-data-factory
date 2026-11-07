"""CSV output. Phase 1 stub."""

from __future__ import annotations

from collections.abc import Iterable
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
    raise NotImplementedError
