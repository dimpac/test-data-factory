"""Independent dataset validation. Phase 1 stub.

Validation reads only the generated CSV files and the expectations. It never uses generators.
"""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel

from tdf.contracts.models import ExpectationSpec
from tdf.metadata.models import SchemaModel


class Outcome(StrEnum):
    SATISFIED = "SATISFIED"
    UNEXPECTED_VIOLATION = "UNEXPECTED_VIOLATION"
    EXPECTED_VIOLATION = "EXPECTED_VIOLATION"
    UNEVALUATED = "UNEVALUATED"


class ValidationResult(BaseModel):
    expectation_id: str
    outcome: Outcome
    evidence: str = ""


def validate_dataset(
    data_dir: Path, schema: SchemaModel, expectations: list[ExpectationSpec]
) -> list[ValidationResult]:
    """Evaluate expectations against `<table>.csv` files in `data_dir`.

    Supported types: completeness, uniqueness, range, enumeration, volume,
    referential_integrity, tuple_in_set. Any other type is UNEVALUATED.
    """
    raise NotImplementedError
