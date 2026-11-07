"""Parse a Mermaid erDiagram into a SchemaModel. Phase 1 stub."""

from __future__ import annotations

from pathlib import Path

from tdf.metadata.models import SchemaModel


class ErdParseError(ValueError):
    """The ERD text is malformed or inconsistent."""


def parse_erd(text: str) -> SchemaModel:
    """Parse ERD text.

    Relationship labels carry join columns as "PARENTCOL=CHILDCOL[,PARENTCOL2=CHILDCOL2]".
    """
    raise NotImplementedError


def load_erd(path: Path) -> SchemaModel:
    raise NotImplementedError
