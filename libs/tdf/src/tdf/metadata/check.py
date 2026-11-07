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
    raise NotImplementedError
