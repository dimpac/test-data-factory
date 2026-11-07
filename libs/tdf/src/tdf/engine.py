"""Plan resolution and relational generation. Phase 1 stub."""

from __future__ import annotations

from typing import Any

from tdf.contracts.models import ContractFile
from tdf.metadata.models import SchemaModel
from tdf.profiling.profiler import ProfileResult


def generate_dataset(
    contracts: ContractFile,
    schema: SchemaModel,
    *,
    seed: int,
    intent: str = "FUNCTIONAL",
    profiles: dict[str, ProfileResult] | None = None,
    row_counts: dict[str, int] | None = None,
) -> dict[str, list[dict[str, Any]]]:
    """Validate contracts, order tables by dependency, and generate rows for every table.

    Validation happens before any generation. Foreign keys draw from already generated parent
    rows. A nullable self-reference references an earlier row, and the first row is null.
    """
    raise NotImplementedError
