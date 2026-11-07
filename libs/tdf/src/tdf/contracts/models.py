"""Generator contract models, aligned with the ontology."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

INTENTS = ("FUNCTIONAL", "PERFORMANCE", "EDGE")


class Target(BaseModel):
    table: str
    columns: list[str] = Field(default_factory=list)


class ExpectationSpec(BaseModel):
    id: str
    type: str  # e.g. completeness, uniqueness, range, enumeration, volume, referential_integrity, tuple_in_set
    scope: Literal["TABLE", "COLUMN", "RELATIONSHIP"]
    target: Target
    params: dict[str, Any] = Field(default_factory=dict)
    source: Literal["INFERRED", "DECLARED", "IMPORTED"] = "DECLARED"
    status: Literal["PROPOSED", "APPROVED", "REJECTED", "RETIRED"] = "APPROVED"


class ColumnGroupSpec(BaseModel):
    name: str
    columns: list[str]
    generator: str
    params: dict[str, Any] = Field(default_factory=dict)


class PolicySpec(BaseModel):
    name: str
    intent: str
    row_count: int
    column_groups: list[ColumnGroupSpec]
    expectations: list[ExpectationSpec] = Field(default_factory=list)


class ContractSpec(BaseModel):
    name: str
    table: str
    version: int = 1
    policies: list[PolicySpec]


class ContractFile(BaseModel):
    database: str
    contracts: list[ContractSpec]
