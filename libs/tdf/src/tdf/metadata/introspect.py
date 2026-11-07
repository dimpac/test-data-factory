"""Read physical table and column types from DuckDB. Phase 1 stub."""

from __future__ import annotations

from pathlib import Path


def introspect_duckdb(path: Path) -> dict[str, dict[str, str]]:
    """Return {table: {column: duckdb_type}} for the database file (opened read-only)."""
    raise NotImplementedError
