"""Plan resolution and relational generation.

Generation is in memory: every table is materialised as a list of dicts before it is written.
"""

from __future__ import annotations

import hashlib
import math
import random
from typing import Any

from tdf.contracts.loader import ContractError
from tdf.contracts.models import ContractFile
from tdf.contracts.validate import validate_contract
from tdf.generators import get_generator
from tdf.metadata.models import SchemaModel
from tdf.planning import generation_order
from tdf.profiling.profiler import ProfileResult


class GenerationError(ValueError):
    """A generator produced output that does not match what its column group requested."""


def _check_group_output(
    table: str, group_name: str, generator: str, columns: list[str], count: int,
    group_rows: list[dict[str, Any]],
) -> None:
    """Every column group must return exactly `count` rows, each with exactly its columns.

    Without this check a short output would leave trailing rows null and a long one would be
    truncated, both silently.
    """
    label = f"Generator {generator!r} for {table}.{group_name}"
    if len(group_rows) != count:
        raise GenerationError(f"{label} returned {len(group_rows)} rows; expected {count}")
    expected = set(columns)
    for index, row in enumerate(group_rows):
        if set(row) != expected:
            missing = sorted(expected - set(row))
            extra = sorted(set(row) - expected)
            raise GenerationError(
                f"{label} row {index} has missing columns {missing} and unexpected columns {extra}"
            )


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
    for table_name, policy in selected.items():
        if row_counts.get(table_name, policy.row_count) < 0:
            raise ContractError(f"Row count for {table_name} cannot be negative")

    def group_seed(table: str, group: str) -> int:
        digest = hashlib.sha256(f"{seed}:{table}:{group}".encode()).digest()
        return int.from_bytes(digest[:8], "big")

    generated: dict[str, list[dict[str, Any]]] = {}
    for table_name in generation_order(schema):
        if table_name not in selected:
            continue
        policy = selected[table_name]
        count = row_counts.get(table_name, policy.row_count)
        rows: list[dict[str, Any]] = [{} for _ in range(count)]
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
            _check_group_output(table_name, group.name, group.generator, group.columns, count, group_rows)
            for row, values in zip(rows, group_rows, strict=True):
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
        return _generate_multi_parent_keys(
            count=count, rng=rng, table=table, columns=columns, params=params,
            parent_specs=parent_specs, generated=generated,
        )

    parent = params.get("parent")
    parent_columns = list(params.get("parent_columns", []))
    if not parent or len(parent_columns) != len(columns):
        raise ContractError(f"Foreign key group for {table}.{columns} has invalid parent parameters")

    if parent == table:
        # Self-references copy keys from earlier rows, so the key columns must already be filled
        # by a column group listed before this one.
        if count > 1:
            missing = [column for column in parent_columns if column not in current_rows[0]]
            if missing:
                raise ContractError(
                    f"Self-referencing foreign key for {table}.{columns} needs {missing} generated "
                    f"first; list that column group before the foreign key group"
                )
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


def _generate_multi_parent_keys(
    *,
    count: int,
    rng: random.Random,
    table: str,
    columns: list[str],
    params: dict[str, Any],
    parent_specs: dict[str, Any],
    generated: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    """One key column per parent table, e.g. orderdetails(ORDERNUMBER, PRODUCTCODE).

    Combinations of parent keys are addressed by index into their (virtual) Cartesian product
    and decoded on demand, so memory is proportional to `count`, not to the product size.
    Each child column references a single-column parent key; composite parent keys and nulls
    are not supported in this mode and are rejected.
    """
    label = f"Foreign key group for {table}.{columns}"
    if params.get("null_ratio"):
        raise ContractError(f"{label}: null_ratio is not supported with 'parents'")
    missing = [column for column in columns if column not in parent_specs]
    unknown = [column for column in parent_specs if column not in columns]
    if missing or unknown:
        raise ContractError(f"{label}: 'parents' is missing {missing} and has unknown {unknown}")

    pools: list[list[Any]] = []
    for column in columns:
        spec = parent_specs[column]
        parent = spec.get("parent") if isinstance(spec, dict) else None
        parent_columns = list(spec.get("parent_columns", [])) if isinstance(spec, dict) else []
        if not parent or len(parent_columns) != 1:
            raise ContractError(
                f"{label}: {column} must name a parent and exactly one parent column "
                f"(composite parent keys are not supported)"
            )
        parent_rows = generated.get(parent)
        if parent_rows is None:
            raise ContractError(f"Parent table {parent} has not been generated")
        if not parent_rows and count:
            raise ContractError(f"Parent table {parent} has no rows")
        pools.append([row[parent_columns[0]] for row in parent_rows])

    total = math.prod(len(pool) for pool in pools)
    if params.get("unique_together"):
        if count > total:
            raise ContractError(
                f"Cannot generate {count} unique references for {table}.{columns}; "
                f"only {total} combinations exist"
            )
        indexes = rng.sample(range(total), count)
    else:
        indexes = [rng.randrange(total) for _ in range(count)]

    def decode(index: int) -> dict[str, Any]:
        values: list[Any] = []
        for pool in reversed(pools):
            index, offset = divmod(index, len(pool))
            values.append(pool[offset])
        return dict(zip(columns, reversed(values)))

    return [decode(index) for index in indexes]
