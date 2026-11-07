import pytest

from tdf.contracts import ContractError, load_contract_file, parse_contract, validate_contract
from tdf.metadata import parse_erd

from ..conftest import STEELWHEELS_CONTRACT

pytestmark = pytest.mark.req("FR-CON-01", "FR-CON-04", "FR-CON-05", "FR-CON-06")

VALID = """
database: demo
contracts:
  - name: orders_contract
    table: orders
    version: 1
    policies:
      - name: orders_functional
        intent: FUNCTIONAL
        row_count: 10
        column_groups:
          - {name: key, columns: [ORDERNUMBER], generator: sequence}
          - {name: status, columns: [STATUS], generator: categorical}
          - {name: customer, columns: [CUSTOMERNUMBER], generator: foreign_key, params: {parent: customers, parent_columns: [CUSTOMERNUMBER]}}
        expectations:
          - {id: e1, type: uniqueness, scope: COLUMN, target: {table: orders, columns: [ORDERNUMBER]}}
"""


def _with(old, new):
    assert old in VALID
    return VALID.replace(old, new)


def test_parse_valid_contract():
    parsed = parse_contract(VALID)
    assert parsed.database == "demo"
    (contract,) = parsed.contracts
    assert contract.table == "orders" and contract.version == 1
    (policy,) = contract.policies
    assert policy.intent == "FUNCTIONAL" and policy.row_count == 10
    assert [g.name for g in policy.column_groups] == ["key", "status", "customer"]
    (exp,) = policy.expectations
    assert exp.source == "DECLARED" and exp.status == "APPROVED"


def test_steelwheels_contract_file_loads_for_all_tables():
    parsed = load_contract_file(STEELWHEELS_CONTRACT)
    assert {c.table for c in parsed.contracts} == {
        "customers", "orders", "orderdetails", "products", "employees", "offices",
    }


def test_unknown_intent_is_rejected():
    with pytest.raises(ContractError, match="intent"):
        parse_contract(_with("intent: FUNCTIONAL", "intent: WHATEVER"))


def test_malformed_yaml_is_rejected():
    with pytest.raises(ContractError):
        parse_contract("database: [unclosed")


def test_valid_contract_passes_validation(small_erd):
    (contract,) = parse_contract(VALID).contracts
    validate_contract(contract, parse_erd(small_erd))


@pytest.mark.req("FR-CON-10")
def test_unknown_table_is_rejected(small_erd):
    (contract,) = parse_contract(_with("table: orders", "table: ghosts")).contracts
    with pytest.raises(ContractError, match="ghosts"):
        validate_contract(contract, parse_erd(small_erd))


@pytest.mark.req("FR-CON-10")
def test_unknown_column_is_rejected(small_erd):
    (contract,) = parse_contract(_with("columns: [STATUS]", "columns: [NOPE]")).contracts
    with pytest.raises(ContractError, match="NOPE"):
        validate_contract(contract, parse_erd(small_erd))


@pytest.mark.req("FR-CON-10")
def test_unsupported_generator_is_rejected(small_erd):
    (contract,) = parse_contract(_with("generator: categorical", "generator: telepathy")).contracts
    with pytest.raises(ContractError, match="telepathy"):
        validate_contract(contract, parse_erd(small_erd))


@pytest.mark.req("FR-CON-09", "AC-06")
def test_overlapping_column_ownership_fails_before_generation(small_erd):
    (contract,) = parse_contract(
        _with("columns: [STATUS]", "columns: [STATUS, ORDERNUMBER]")
    ).contracts
    with pytest.raises(ContractError) as exc:
        validate_contract(contract, parse_erd(small_erd))
    message = str(exc.value)
    assert "ORDERNUMBER" in message and "key" in message and "status" in message
