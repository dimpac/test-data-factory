"""Table profiling with DuckDB and pandas. Phase 1 stub."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

VALUE_SET_CAP = 100  # provisional AD-005

METRICS = (
    "row_count", "null_count", "non_null_count", "distinct_non_null_count",
    "min", "max", "mean", "stddev", "value_set", "value_frequencies",
)


class Observation(BaseModel):
    metric: str
    columns: list[str]  # one column, or several for multi-column value sets
    value: Any
    segment: str = "ALL"  # provisional AD-004


class ProfileResult(BaseModel):
    id: str
    table: str
    created_at: datetime
    config: dict[str, Any] = Field(default_factory=dict)
    observations: list[Observation] = Field(default_factory=list)


def profile_table(
    connection: Any,
    table: str,
    *,
    columns: list[str] | None = None,
    tuple_sets: list[list[str]] | None = None,
) -> ProfileResult:
    """Profile a whole table.

    `stddev` is the sample standard deviation. `value_set` and `value_frequencies` are produced
    only for columns with at most VALUE_SET_CAP distinct non-null values. `tuple_sets` requests
    multi-column `value_set` observations (distinct combinations, nulls preserved).
    """
    raise NotImplementedError
