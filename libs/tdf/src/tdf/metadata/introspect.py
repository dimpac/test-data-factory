"""Read physical table and column types from DuckDB. Phase 1 stub."""

from __future__ import annotations

from pathlib import Path


def introspect_duckdb(path: Path) -> dict[str, dict[str, str]]:
    """Return {table: {column: duckdb_type}} for the database file (opened read-only)."""
    import duckdb

    with duckdb.connect(str(path), read_only=True) as connection:
        tables = connection.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'main' ORDER BY table_name"
        ).fetchall()
        return {
            table: {
                row[0]: row[1]
                for row in connection.execute(f"DESCRIBE SELECT * FROM \"{table}\"").fetchall()
            }
            for (table,) in tables
        }
