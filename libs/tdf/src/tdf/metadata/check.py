"""Compare the declared schema with the physical database. Phase 1 stub."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from tdf.metadata.models import SchemaModel


class Issue(BaseModel):
    severity: Literal["error", "warning"]
    message: str


def check_schema(schema: SchemaModel, physical: dict[str, dict[str, str]]) -> list[Issue]:
    """Missing tables or columns are errors; type mismatches are warnings."""
    aliases = {
        "string": "VARCHAR",
        "int": "INTEGER",
        "integer": "INTEGER",
        "bigint": "BIGINT",
        "decimal": "DECIMAL",
        "date": "DATE",
        "timestamp": "TIMESTAMP",
        "boolean": "BOOLEAN",
        "float": "FLOAT",
    }
    issues: list[Issue] = []
    for table_name, table in schema.tables.items():
        if table_name not in physical:
            issues.append(Issue(severity="error", message=f"Missing table {table_name}"))
            continue
        actual_columns = physical[table_name]
        for column in table.columns:
            qualified = f"{table_name}.{column.name}"
            if column.name not in actual_columns:
                issues.append(Issue(severity="error", message=f"Missing column {qualified}"))
                continue
            expected = aliases.get(column.type.lower(), column.type.upper())
            actual = actual_columns[column.name].upper()
            if not (actual == expected or actual.startswith(f"{expected}(") or
                    (expected == "DECIMAL" and actual.startswith("DECIMAL"))):
                issues.append(
                    Issue(severity="warning", message=f"Type mismatch for {qualified}: {column.type} vs {actual}")
                )
    return issues
