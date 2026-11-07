"""Schema metadata models (Database, Table, Column, RELATES_TO)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class Column(BaseModel):
    name: str
    type: str
    primary_key: bool = False
    foreign_key: bool = False


class Table(BaseModel):
    name: str
    columns: list[Column]


class Relationship(BaseModel):
    """A RELATES_TO edge. The parent owns the referenced key; the child holds the reference."""

    parent: str
    child: str
    parent_columns: list[str]
    child_columns: list[str]
    cardinality: str = "one_to_many"
    optional: bool = False  # True when the child reference may be null


class SchemaModel(BaseModel):
    tables: dict[str, Table] = Field(default_factory=dict)
    relationships: list[Relationship] = Field(default_factory=list)
