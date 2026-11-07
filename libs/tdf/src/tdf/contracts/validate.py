"""Pre-execution contract validation. Phase 1 stub."""

from __future__ import annotations

from tdf.contracts.models import ContractSpec
from tdf.metadata.models import SchemaModel
from tdf.contracts.loader import ContractError
from tdf.generators import available_generators


def validate_contract(contract: ContractSpec, schema: SchemaModel) -> None:
    """Raise ContractError for unknown tables, columns or generators, or for columns owned
    by more than one column group within a policy (provisional AD-008)."""
    if contract.table not in schema.tables:
        raise ContractError(f"Unknown table {contract.table}")
    table_columns = {column.name for column in schema.tables[contract.table].columns}
    generators = available_generators()
    for policy in contract.policies:
        owners: dict[str, str] = {}
        for group in policy.column_groups:
            if group.generator not in generators:
                raise ContractError(f"Unsupported generator {group.generator}")
            for column in group.columns:
                if column not in table_columns:
                    raise ContractError(f"Unknown column {contract.table}.{column}")
                if column in owners:
                    raise ContractError(
                        f"Column {column} is owned by both {owners[column]} and {group.name}"
                    )
                owners[column] = group.name
