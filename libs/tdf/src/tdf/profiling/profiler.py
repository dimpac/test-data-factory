"""Table profiling with DuckDB and pandas. Phase 1 stub."""

from __future__ import annotations

from datetime import datetime
from typing import Any
import uuid

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
    value_set_columns: list[str] | None = None,
) -> ProfileResult:
    """Profile a whole table.

    `stddev` is the sample standard deviation. `value_set` and `value_frequencies` are produced
    only for columns with at most VALUE_SET_CAP distinct non-null values. `tuple_sets` requests
    multi-column `value_set` observations (distinct combinations, nulls preserved).
    `value_set_columns` opts named columns in to a full value list even above VALUE_SET_CAP,
    so generators can draw real values (e.g. customer names) from the source.
    """
    def quote(identifier: str) -> str:
        return '"' + identifier.replace('"', '""') + '"'

    described = connection.execute(f"DESCRIBE SELECT * FROM {quote(table)}").fetchall()
    types = {row[0]: row[1].upper() for row in described}
    selected = columns or list(types)
    unknown = set(selected) - set(types)
    if unknown:
        raise ValueError(f"Unknown columns for {table}: {', '.join(sorted(unknown))}")

    observations: list[Observation] = []
    for column in selected:
        identifier = quote(column)
        row_count, null_count, non_null_count, distinct_count = connection.execute(
            f"SELECT count(*), count(*) FILTER (WHERE {identifier} IS NULL), "
            f"count({identifier}), count(DISTINCT {identifier}) FROM {quote(table)}"
        ).fetchone()
        values = {
            "row_count": row_count,
            "null_count": null_count,
            "non_null_count": non_null_count,
            "distinct_non_null_count": distinct_count,
        }
        observations.extend(
            Observation(metric=metric, columns=[column], value=value)
            for metric, value in values.items()
        )

        type_name = types[column]
        if any(token in type_name for token in ("INT", "DECIMAL", "NUMERIC", "DOUBLE", "FLOAT", "REAL")):
            minimum, maximum, mean, stddev = connection.execute(
                f"SELECT min({identifier}), max({identifier}), avg({identifier}), "
                f"stddev_samp({identifier}) FROM {quote(table)}"
            ).fetchone()
            observations.extend(
                Observation(metric=metric, columns=[column], value=value)
                for metric, value in (
                    ("min", minimum), ("max", maximum), ("mean", mean), ("stddev", stddev)
                )
            )

        # Bounded value catalogues are useful for categorical text, not numeric identifiers.
        opted_in = column in (value_set_columns or [])
        if (distinct_count <= VALUE_SET_CAP or opted_in) and any(
            token in type_name for token in ("CHAR", "VARCHAR", "TEXT", "ENUM", "BOOL")
        ):
            frequencies = connection.execute(
                f"SELECT {identifier}, count(*) FROM {quote(table)} "
                f"WHERE {identifier} IS NOT NULL GROUP BY {identifier} ORDER BY {identifier}"
            ).fetchall()
            observations.append(
                Observation(metric="value_set", columns=[column], value=[row[0] for row in frequencies])
            )
            observations.append(
                Observation(
                    metric="value_frequencies",
                    columns=[column],
                    value={str(value): count for value, count in frequencies},
                )
            )

    for tuple_columns in tuple_sets or []:
        unknown = set(tuple_columns) - set(types)
        if unknown:
            raise ValueError(f"Unknown columns for {table}: {', '.join(sorted(unknown))}")
        projection = ", ".join(quote(column) for column in tuple_columns)
        rows = connection.execute(
            f"SELECT DISTINCT {projection} FROM {quote(table)} ORDER BY {projection}"
        ).fetchall()
        observations.append(
            Observation(metric="value_set", columns=tuple_columns, value=[list(row) for row in rows])
        )

    return ProfileResult(
        id=uuid.uuid4().hex,
        table=table,
        created_at=datetime.now(),
        config={"columns": columns, "tuple_sets": tuple_sets or []},
        observations=observations,
    )
