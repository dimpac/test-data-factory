"""Load YAML contracts. Phase 1 stub."""

from __future__ import annotations

from pathlib import Path

from tdf.contracts.models import ContractFile


class ContractError(ValueError):
    """A contract is malformed or fails validation."""


def parse_contract(text: str) -> ContractFile:
    """Parse YAML text. Unknown intents are rejected with ContractError."""
    raise NotImplementedError


def load_contract_file(path: Path) -> ContractFile:
    raise NotImplementedError
