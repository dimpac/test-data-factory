"""Plan resolution and relational generation. Phase 1 stub."""

from __future__ import annotations

import hashlib
import itertools
import random
from typing import Any

from tdf.contracts.loader import ContractError
from tdf.contracts.models import ContractFile
from tdf.contracts.validate import validate_contract
from tdf.generators import get_generator
from tdf.metadata.models import SchemaModel
from tdf.planning import generation_order
from tdf.profiling.profiler import ProfileResult


def generate_dataset(
    contracts: ContractFile,
    schema: SchemaModel,
    *,
    seed: int,
    intent: str = "FUNCTIONAL",
    profiles: dict[str, ProfileResult] | None = None,
    row_counts: dict[str, int] | None = None,
) -> dict[str, list[dict[str, Any]]]:
    """Validate contracts, order tables by dependency, and generate rows for every table.

    Validation happens before any generation. Foreign keys draw from already generated parent
    rows. A nullable self-reference references an earlier row, and the first row is null.
    """
    profiles = profiles or {}
    row_counts = row_counts or {}
    by_table = {contract.table: contract for contract in contracts.contracts}

    # Resolve every policy and validate every contract before producing any data.
    selected: dict[str, Any] = {}
    for contract in contracts.contracts:
        validate_contract(contract, schema)
        policy = next((item for item in contract.policies if item.intent == intent), None)
        if policy is None:
            raise ContractError(f"Contract for {contract.table} has no {intent} policy")
        selected[contract.table] = policy
    unknown_overrides = set(row_counts) - set(by_table)
    if unknown_overrides:
        raise ContractError(f"Row count overrides name unknown tables: {', '.join(sorted(unknown_overrides))}")
    if any(value < 0 for value in row_counts.values()):
        raise ContractError("Row counts cannot be negative")

    def group_seed(table: str, group: str) -> int:
        digest = hashlib.sha256(f"{seed}:{table}:{group}".encode()).digest()
        return int.from_bytes(digest[:8], "big")

    generated: dict[str, list[dict[str, Any]]] = {}
    for table_name in generation_order(schema):
        if table_name not in selected:
            continue
        policy = selected[table_name]
        count = row_counts.get(table_name, policy.row_count)
        rows = [{} for _ in range(count)]
        for group in policy.column_groups:
            current_seed = group_seed(table_name, group.name)
            if group.generator == "foreign_key":
                group_rows = _generate_foreign_keys(
                    count=count,
                    seed=current_seed,
                    table=table_name,
                    columns=group.columns,
                    params=group.params,
                    generated=generated,
                    current_rows=rows,
                )
            else:
                group_rows = get_generator(group.generator).generate(
                    count=count,
                    seed=current_seed,
                    columns=group.columns,
                    params=group.params,
                    profile=profiles.get(table_name),
                )
            for row, values in zip(rows, group_rows):
                row.update(values)

        declared_columns = [column.name for column in schema.tables[table_name].columns]
        for row in rows:
            for column in declared_columns:
                row.setdefault(column, None)
            # Preserve declared schema order in output dictionaries.
            ordered = {column: row[column] for column in declared_columns}
            row.clear()
            row.update(ordered)
        generated[table_name] = rows
    return generated


def _generate_foreign_keys(
    *,
    count: int,
    seed: int,
    table: str,
    columns: list[str],
    params: dict[str, Any],
    generated: dict[str, list[dict[str, Any]]],
    current_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Generate references from parent rows already present in the dataset."""
    rng = random.Random(seed)
    null_ratio = float(params.get("null_ratio", 0.0))

    parent_specs = params.get("parents")
    if parent_specs:
        pools: list[list[Any]] = []
        for column in columns:
            spec = parent_specs[column]
            parent_rows = generated.get(spec["parent"])
            if parent_rows is None:
                raise ContractError(f"Parent table {spec['parent']} has not been generated")
            parent_column = spec["parent_columns"][0]
            pools.append([row[parent_column] for row in parent_rows])
        combinations = list(itertools.product(*pools))
        if params.get("unique_together"):
            if count > len(combinations):
                raise ContractError(
                    f"Cannot generate {count} unique references for {table}.{columns}; "
                    f"only {len(combinations)} combinations exist"
                )
            rng.shuffle(combinations)
            selected = combinations[:count]
        else:
            selected = [rng.choice(combinations) for _ in range(count)]
        return [dict(zip(columns, values)) for values in selected]

    parent = params.get("parent")
    parent_columns = list(params.get("parent_columns", []))
    if not parent or len(parent_columns) != len(columns):
        raise ContractError(f"Foreign key group for {table}.{columns} has invalid parent parameters")

    if parent == table:
        output: list[dict[str, Any]] = []
        for index in range(count):
            if index == 0 or rng.random() < null_ratio:
                output.append({column: None for column in columns})
                continue
            source = current_rows[rng.randrange(index)]
            output.append({column: source[parent_column]
                           for column, parent_column in zip(columns, parent_columns)})
        return output

    parent_rows = generated.get(parent)
    if parent_rows is None:
        raise ContractError(f"Parent table {parent} has not been generated")
    if not parent_rows and count:
        raise ContractError(f"Parent table {parent} has no rows")
    output = []
    for _ in range(count):
        if null_ratio and rng.random() < null_ratio:
            output.append({column: None for column in columns})
        else:
            source = rng.choice(parent_rows)
            output.append({column: source[parent_column]
                           for column, parent_column in zip(columns, parent_columns)})
    return output
