#!/usr/bin/env python3
"""Build the local SteelWheels DuckDB database from repository CSV files."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

import duckdb


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def quote_identifier(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def quote_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Rebuild a DuckDB database from CSV files."
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=REPOSITORY_ROOT / "data",
        help="directory containing CSV files",
    )
    parser.add_argument(
        "--database",
        type=Path,
        default=REPOSITORY_ROOT / "data" / "steelwheels.duckdb",
        help="database artifact to create",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    data_dir = args.data_dir.resolve()
    database = args.database.resolve()
    csv_files = (
        sorted(
            (
                path
                for path in data_dir.iterdir()
                if path.is_file() and path.suffix.casefold() == ".csv"
            ),
            key=lambda path: path.name.casefold(),
        )
        if data_dir.is_dir()
        else []
    )

    if not csv_files:
        print(f"No CSV files found in {data_dir}; skipping SteelWheels setup.")
        return 0

    table_names: set[str] = set()
    for csv_file in csv_files:
        normalized_name = csv_file.stem.casefold()
        if normalized_name in table_names:
            raise ValueError(
                f"CSV filenames must have unique stems: {csv_file.stem!r}"
            )
        table_names.add(normalized_name)

    database.parent.mkdir(parents=True, exist_ok=True)
    temporary_database = database.with_name(f".{database.name}.tmp")
    temporary_wal = temporary_database.with_suffix(
        f"{temporary_database.suffix}.wal"
    )
    temporary_database.unlink(missing_ok=True)
    temporary_wal.unlink(missing_ok=True)

    try:
        with duckdb.connect(str(temporary_database)) as connection:
            for csv_file in csv_files:
                connection.execute(
                    f"CREATE TABLE {quote_identifier(csv_file.stem)} AS "
                    f"SELECT * FROM read_csv({quote_literal(str(csv_file.resolve()))}, "
                    "header = true, auto_detect = true)"
                )
        os.replace(temporary_database, database)
        database.with_suffix(f"{database.suffix}.wal").unlink(missing_ok=True)
    except Exception:
        temporary_database.unlink(missing_ok=True)
        temporary_wal.unlink(missing_ok=True)
        raise

    tables = ", ".join(csv_file.stem for csv_file in csv_files)
    print(f"Created {database} with tables: {tables}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
