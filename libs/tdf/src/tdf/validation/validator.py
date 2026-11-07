"""Independent dataset validation. Phase 1 stub.

Validation reads only the generated CSV files and the expectations. It never uses generators.
"""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
import csv
from collections import Counter
from typing import Any

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
    del schema  # Schema metadata is intentionally not used to reproduce generation behavior.
    cache: dict[str, list[dict[str, str | None]]] = {}

    def rows(table: str) -> list[dict[str, str | None]]:
        if table not in cache:
            with (Path(data_dir) / f"{table}.csv").open(newline="") as handle:
                cache[table] = [
                    {key: (value if value != "" else None) for key, value in row.items()}
                    for row in csv.DictReader(handle)
                ]
        return cache[table]

    def values(table: str, columns: list[str]) -> list[tuple[str | None, ...]]:
        return [tuple(row.get(column) for column in columns) for row in rows(table)]

    def normalise(value: Any) -> str | None:
        return None if value is None else str(value)

    results: list[ValidationResult] = []
    supported = {
        "completeness", "uniqueness", "range", "enumeration", "volume",
        "referential_integrity", "tuple_in_set",
    }
    for expectation in expectations:
        if expectation.type not in supported:
            results.append(ValidationResult(expectation_id=expectation.id, outcome=Outcome.UNEVALUATED))
            continue
        table = expectation.target.table
        columns = expectation.target.columns
        params = expectation.params
        offending: list[Any] = []
        table_rows = rows(table)

        if expectation.type == "uniqueness":
            tuples = values(table, columns)
            offending = [value for value, count in Counter(tuples).items() if count > 1]
        elif expectation.type == "referential_integrity":
            child_values = values(table, columns)
            parent_values = set(values(params["parent"], params["parent_columns"]))
            offending = [value for value in child_values if all(v is not None for v in value) and value not in parent_values]
        elif expectation.type == "completeness":
            total = len(table_rows)
            null_count = sum(
                1 for row in table_rows if any(row.get(column) is None for column in columns)
            )
            ratio = null_count / total if total else 0.0
            if ratio > float(params.get("max_null_ratio", 0.0)):
                offending = [f"null_ratio={ratio}"]
        elif expectation.type == "range":
            minimum, maximum = params.get("min"), params.get("max")
            for value in values(table, columns):
                for item in value:
                    if item is None:
                        continue
                    try:
                        comparable: Any = float(item)
                    except ValueError:
                        comparable = item
                    if ((minimum is not None and comparable < minimum) or
                            (maximum is not None and comparable > maximum)):
                        offending.append(item)
        elif expectation.type == "enumeration":
            allowed = {normalise(value) for value in params.get("values", [])}
            offending = [item for value in values(table, columns) for item in value
                          if item is not None and item not in allowed]
        elif expectation.type == "volume":
            count = len(table_rows)
            if count < int(params.get("min", 0)) or count > int(params.get("max", count)):
                offending = [f"row_count={count}"]
        elif expectation.type == "tuple_in_set":
            allowed = {
                tuple(normalise(item) for item in value)
                for value in params.get("values", [])
            }
            offending = [value for value in values(table, columns) if value not in allowed]

        if offending:
            outcome = (Outcome.EXPECTED_VIOLATION if params.get("expect_violation")
                       else Outcome.UNEXPECTED_VIOLATION)
            evidence = repr(offending[:10])
        else:
            outcome = Outcome.SATISFIED
            evidence = ""
        results.append(
            ValidationResult(expectation_id=expectation.id, outcome=outcome, evidence=evidence)
        )
    return results
