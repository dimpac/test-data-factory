"""Independent dataset validation.

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
    referential_integrity, tuple_in_set. Any other type is UNEVALUATED, as is any expectation
    whose status is not APPROVED.

    A misconfigured expectation (missing CSV, unknown column, missing parameter) is reported as
    UNEXPECTED_VIOLATION with "configuration error" evidence. It can never be SATISFIED.

    Limitation: an expectation marked `expect_violation` that is not violated is reported as
    SATISFIED. How negative tests should report this is open (AD-013).
    """
    del schema  # Schema metadata is intentionally not used to reproduce generation behavior.
    cache: dict[str, tuple[list[str], list[dict[str, str | None]]]] = {}

    def load(table: str) -> tuple[list[str], list[dict[str, str | None]]]:
        if table not in cache:
            path = Path(data_dir) / f"{table}.csv"
            if not path.is_file():
                raise _ConfigurationError(f"no data file {path.name}")
            with path.open(newline="") as handle:
                reader = csv.DictReader(handle)
                data = [
                    {key: (value if value != "" else None) for key, value in row.items()}
                    for row in reader
                ]
                cache[table] = (list(reader.fieldnames or []), data)
        return cache[table]

    def rows(table: str) -> list[dict[str, str | None]]:
        return load(table)[1]

    def require_columns(table: str, columns: list[str]) -> None:
        header = load(table)[0]
        unknown = [column for column in columns if column not in header]
        if unknown:
            raise _ConfigurationError(f"unknown columns {unknown} in {table}")

    def require(params: dict[str, Any], *names: str) -> None:
        missing = [name for name in names if params.get(name) in (None, [], "")]
        if missing:
            raise _ConfigurationError(f"missing parameters {missing}")

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
        if expectation.status != "APPROVED":
            results.append(ValidationResult(
                expectation_id=expectation.id, outcome=Outcome.UNEVALUATED,
                evidence=f"status {expectation.status}; only APPROVED expectations are evaluated",
            ))
            continue
        if expectation.type not in supported:
            results.append(ValidationResult(
                expectation_id=expectation.id, outcome=Outcome.UNEVALUATED,
                evidence=f"unsupported expectation type {expectation.type!r}",
            ))
            continue
        try:
            offending = _evaluate(expectation, rows, values, require_columns, require, normalise)
        except _ConfigurationError as exc:
            results.append(ValidationResult(
                expectation_id=expectation.id, outcome=Outcome.UNEXPECTED_VIOLATION,
                evidence=f"configuration error: {exc}",
            ))
            continue

        if offending:
            outcome = (Outcome.EXPECTED_VIOLATION if expectation.params.get("expect_violation")
                       else Outcome.UNEXPECTED_VIOLATION)
            evidence = repr(offending[:10])
        else:
            outcome = Outcome.SATISFIED
            evidence = ""
        results.append(
            ValidationResult(expectation_id=expectation.id, outcome=outcome, evidence=evidence)
        )
    return results


class _ConfigurationError(Exception):
    """The expectation cannot be evaluated against the data as written."""


def _evaluate(expectation, rows, values, require_columns, require, normalise) -> list[Any]:
    """Return offending values for one supported expectation (empty when satisfied)."""
    table = expectation.target.table
    columns = expectation.target.columns
    params = expectation.params
    table_rows = rows(table)
    require_columns(table, columns)
    if expectation.type != "volume" and not columns:
        raise _ConfigurationError(f"{expectation.type} needs target columns")

    if expectation.type == "uniqueness":
        tuples = values(table, columns)
        return [value for value, count in Counter(tuples).items() if count > 1]

    if expectation.type == "referential_integrity":
        require(params, "parent", "parent_columns")
        if len(params["parent_columns"]) != len(columns):
            raise _ConfigurationError("parent_columns and target columns differ in length")
        require_columns(params["parent"], params["parent_columns"])
        parent_values = set(values(params["parent"], params["parent_columns"]))
        return [value for value in values(table, columns)
                if all(v is not None for v in value) and value not in parent_values]

    if expectation.type == "completeness":
        total = len(table_rows)
        null_count = sum(
            1 for row in table_rows if any(row.get(column) is None for column in columns)
        )
        ratio = null_count / total if total else 0.0
        return [f"null_ratio={ratio}"] if ratio > float(params.get("max_null_ratio", 0.0)) else []

    if expectation.type == "range":
        minimum, maximum = params.get("min"), params.get("max")
        if minimum is None and maximum is None:
            raise _ConfigurationError("range needs min or max")
        numeric = all(isinstance(bound, (int, float)) for bound in (minimum, maximum)
                      if bound is not None)
        offending: list[Any] = []
        for value in values(table, columns):
            for item in value:
                if item is None:
                    continue
                comparable: Any = item
                if numeric:
                    try:
                        comparable = float(item)
                    except ValueError:
                        # A non-numeric value cannot satisfy a numeric range.
                        offending.append(item)
                        continue
                if ((minimum is not None and comparable < minimum) or
                        (maximum is not None and comparable > maximum)):
                    offending.append(item)
        return offending

    if expectation.type == "enumeration":
        require(params, "values")
        allowed = {normalise(value) for value in params["values"]}
        return [item for value in values(table, columns) for item in value
                if item is not None and item not in allowed]

    if expectation.type == "volume":
        count = len(table_rows)
        if count < int(params.get("min", 0)) or count > int(params.get("max", count)):
            return [f"row_count={count}"]
        return []

    if expectation.type == "tuple_in_set":
        require(params, "values")
        allowed = {tuple(normalise(item) for item in value) for value in params["values"]}
        return [value for value in values(table, columns) if value not in allowed]

    raise _ConfigurationError(f"no evaluator for {expectation.type}")
