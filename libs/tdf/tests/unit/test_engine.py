from datetime import datetime

import pytest

from tdf.contracts import ContractError, parse_contract
from tdf.engine import generate_dataset
from tdf.metadata import Column, Relationship, SchemaModel, Table, parse_erd
from tdf.profiling import Observation, ProfileResult

pytestmark = pytest.mark.req("FR-GEN-08", "FR-GEN-10", "AC-01")

CONTRACT = """
database: demo
contracts:
  - name: customers_contract
    table: customers
    policies:
      - name: p
        intent: FUNCTIONAL
        row_count: 20
        column_groups:
          - {name: key, columns: [CUSTOMERNUMBER], generator: sequence, params: {start: 1}}
          - {name: name, columns: [CUSTOMERNAME], generator: string}
          - {name: loc, columns: [CITY, STATE, COUNTRY], generator: tuple, params: {source: profile}}
  - name: orders_contract
    table: orders
    policies:
      - name: p
        intent: FUNCTIONAL
        row_count: 50
        column_groups:
          - {name: key, columns: [ORDERNUMBER], generator: sequence, params: {start: 100}}
          - {name: status, columns: [STATUS], generator: categorical, params: {values: [Shipped, Cancelled]}}
          - {name: cust, columns: [CUSTOMERNUMBER], generator: foreign_key, params: {parent: customers, parent_columns: [CUSTOMERNUMBER]}}
"""

PROFILE = ProfileResult(
    id="p", table="customers", created_at=datetime(2026, 1, 1),
    observations=[Observation(metric="value_set", columns=["CITY", "STATE", "COUNTRY"],
                              value=[["Boston", "MA", "USA"], ["Paris", None, "France"]])],
)


def _generate(small_erd, seed=42, contract=CONTRACT, **kwargs):
    return generate_dataset(
        parse_contract(contract), parse_erd(small_erd), seed=seed,
        profiles={"customers": PROFILE}, **kwargs,
    )


def test_requested_row_counts_are_honoured(small_erd):
    data = _generate(small_erd)
    assert len(data["customers"]) == 20 and len(data["orders"]) == 50


def test_row_count_override(small_erd):
    data = _generate(small_erd, row_counts={"customers": 5, "orders": 8})
    assert len(data["customers"]) == 5 and len(data["orders"]) == 8


def test_every_order_references_a_generated_customer(small_erd):
    data = _generate(small_erd)
    customers = {r["CUSTOMERNUMBER"] for r in data["customers"]}
    assert {r["CUSTOMERNUMBER"] for r in data["orders"]} <= customers


def test_same_seed_gives_identical_dataset(small_erd):
    assert _generate(small_erd, seed=5) == _generate(small_erd, seed=5)


def test_different_seed_gives_different_dataset(small_erd):
    assert _generate(small_erd, seed=1) != _generate(small_erd, seed=2)


def test_rows_contain_every_declared_column(small_erd):
    data = _generate(small_erd)
    assert set(data["orders"][0]) == {"ORDERNUMBER", "STATUS", "CUSTOMERNUMBER"}


def test_invalid_contract_fails_before_any_generation(small_erd):
    bad = CONTRACT.replace("columns: [STATUS]", "columns: [STATUS, ORDERNUMBER]")
    with pytest.raises(ContractError):
        _generate(small_erd, contract=bad)


def test_nullable_self_reference_points_to_earlier_row():
    schema = SchemaModel(
        tables={"emp": Table(name="emp", columns=[Column(name="ID", type="int", primary_key=True),
                                                  Column(name="BOSS", type="int", foreign_key=True)])},
        relationships=[Relationship(parent="emp", child="emp", parent_columns=["ID"],
                                    child_columns=["BOSS"], optional=True)],
    )
    contract = parse_contract("""
database: demo
contracts:
  - name: c
    table: emp
    policies:
      - name: p
        intent: FUNCTIONAL
        row_count: 30
        column_groups:
          - {name: key, columns: [ID], generator: sequence, params: {start: 1}}
          - {name: boss, columns: [BOSS], generator: foreign_key, params: {parent: emp, parent_columns: [ID]}}
""")
    rows = generate_dataset(contract, schema, seed=1)["emp"]
    assert rows[0]["BOSS"] is None
    for row in rows[1:]:
        assert row["BOSS"] is not None and row["BOSS"] < row["ID"]


def test_nullable_foreign_key_may_be_null_but_never_dangling(small_erd):
    nullable = CONTRACT.replace(
        "params: {parent: customers, parent_columns: [CUSTOMERNUMBER]}",
        "params: {parent: customers, parent_columns: [CUSTOMERNUMBER], null_ratio: 0.3}",
    )
    data = _generate(small_erd, contract=nullable)
    customers = {r["CUSTOMERNUMBER"] for r in data["customers"]}
    refs = [r["CUSTOMERNUMBER"] for r in data["orders"]]
    assert any(v is None for v in refs)
    assert {v for v in refs if v is not None} <= customers
