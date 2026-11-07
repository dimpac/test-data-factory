"""Pre-execution contract validation. Phase 1 stub."""

from __future__ import annotations

from tdf.contracts.models import ContractSpec
from tdf.metadata.models import SchemaModel


def validate_contract(contract: ContractSpec, schema: SchemaModel) -> None:
    """Raise ContractError for unknown tables, columns or generators, or for columns owned
    by more than one column group within a policy (provisional AD-008)."""
    raise NotImplementedError
