"""Load YAML contracts. Phase 1 stub."""

from __future__ import annotations

from pathlib import Path
import yaml
from pydantic import ValidationError

from tdf.contracts.models import INTENTS, ContractFile


class ContractError(ValueError):
    """A contract is malformed or fails validation."""


def parse_contract(text: str) -> ContractFile:
    """Parse YAML text. Unknown intents are rejected with ContractError."""
    try:
        value = yaml.safe_load(text)
        contract_file = ContractFile.model_validate(value)
    except (yaml.YAMLError, ValidationError, TypeError) as exc:
        raise ContractError(str(exc)) from exc
    for contract in contract_file.contracts:
        for policy in contract.policies:
            if policy.intent not in INTENTS:
                raise ContractError(f"Unknown intent {policy.intent!r}")
    return contract_file


def load_contract_file(path: Path) -> ContractFile:
    return parse_contract(Path(path).read_text())
