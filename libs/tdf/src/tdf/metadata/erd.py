"""Parse a Mermaid ``erDiagram`` into schema metadata."""

from __future__ import annotations

from pathlib import Path
import re

from tdf.metadata.models import Column, Relationship, SchemaModel, Table


class ErdParseError(ValueError):
    """The ERD text is malformed or inconsistent."""


def parse_erd(text: str) -> SchemaModel:
    """Parse ERD text.

    Relationship labels carry join columns as "PARENTCOL=CHILDCOL[,PARENTCOL2=CHILDCOL2]".
    """
    tables: dict[str, Table] = {}
    relationships: list[tuple[str, str, str, str]] = []
    current: str | None = None

    relation_re = re.compile(
        r'^\s*([\w-]+)\s+([|o}{]+)--([|o}{]+)\s+([\w-]+)\s*:\s*"([^"]*)"'
    )
    table_re = re.compile(r"^\s*([\w-]+)\s*\{\s*$")
    column_re = re.compile(r"^\s*(\S+)\s+(\S+)(?:\s+(.*?))?\s*$")

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line == "erDiagram" or line.startswith("%%"):
            continue
        relation = relation_re.match(raw_line)
        if relation:
            parent, left, _right, child, label = relation.groups()
            relationships.append((parent.lower(), child.lower(), left, label))
            continue
        table = table_re.match(raw_line)
        if table:
            current = table.group(1).lower()
            tables[current] = Table(name=current, columns=[])
            continue
        if line == "}":
            current = None
            continue
        if current:
            column = column_re.match(raw_line)
            if not column:
                raise ErdParseError(f"Invalid column declaration: {line}")
            type_name, name, markers = column.groups()
            flags = {part.strip().upper() for part in (markers or "").split(",")}
            tables[current].columns.append(
                Column(
                    name=name.upper(),
                    type=type_name.lower(),
                    primary_key="PK" in flags,
                    foreign_key="FK" in flags,
                )
            )

    parsed_relationships: list[Relationship] = []
    for parent, child, left, label in relationships:
        if parent not in tables:
            raise ErdParseError(f"Relationship names unknown table {parent}")
        if child not in tables:
            raise ErdParseError(f"Relationship names unknown table {child}")
        if not label.strip():
            raise ErdParseError(f"Relationship {parent}->{child} requires join columns")
        parent_columns: list[str] = []
        child_columns: list[str] = []
        for item in label.split(","):
            if "=" not in item:
                raise ErdParseError(f"Invalid relationship join {item!r}")
            parent_column, child_column = (part.strip().upper() for part in item.split("=", 1))
            parent_names = {column.name for column in tables[parent].columns}
            child_names = {column.name for column in tables[child].columns}
            if parent_column not in parent_names:
                raise ErdParseError(f"Unknown column {parent_column} on {parent}")
            if child_column not in child_names:
                raise ErdParseError(f"Unknown column {child_column} on {child}")
            parent_columns.append(parent_column)
            child_columns.append(child_column)
        parsed_relationships.append(
            Relationship(
                parent=parent,
                child=child,
                parent_columns=parent_columns,
                child_columns=child_columns,
                optional="o" in left,
            )
        )
    return SchemaModel(tables=tables, relationships=parsed_relationships)


def load_erd(path: Path) -> SchemaModel:
    return parse_erd(Path(path).read_text())
