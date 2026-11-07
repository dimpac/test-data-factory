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


# --- Generator output cardinality (review P0.1) -------------------------------------------------

def _patch_string_generator(monkeypatch, transform):
    from tdf.generators import registry

    original = registry._BuiltInGenerator.generate

    def patched(self, **kwargs):
        rows = original(self, **kwargs)
        return transform(rows) if self.name == "string" else rows

    monkeypatch.setattr(registry._BuiltInGenerator, "generate", patched)


def test_exact_generator_output_is_accepted(small_erd, monkeypatch):
    _patch_string_generator(monkeypatch, lambda rows: rows)
    assert len(_generate(small_erd)["customers"]) == 20


def test_insufficient_generator_output_fails(small_erd, monkeypatch):
    from tdf.engine import GenerationError

    _patch_string_generator(monkeypatch, lambda rows: rows[:-2])
    with pytest.raises(GenerationError, match=r"'string' for customers\.name returned 18 rows; expected 20"):
        _generate(small_erd)


def test_excessive_generator_output_fails(small_erd, monkeypatch):
    from tdf.engine import GenerationError

    _patch_string_generator(monkeypatch, lambda rows: rows + rows[:1])
    with pytest.raises(GenerationError, match="returned 21 rows; expected 20"):
        _generate(small_erd)


def test_generator_output_missing_its_column_fails(small_erd, monkeypatch):
    from tdf.engine import GenerationError

    _patch_string_generator(monkeypatch, lambda rows: [{} for _ in rows])
    with pytest.raises(GenerationError, match=r"missing columns \['CUSTOMERNAME'\]"):
        _generate(small_erd)


def test_negative_policy_row_count_is_rejected(small_erd):
    with pytest.raises(ContractError, match="customers cannot be negative"):
        _generate(small_erd, contract=CONTRACT.replace("row_count: 20", "row_count: -1"))


def test_zero_rows_are_allowed(small_erd):
    data = _generate(small_erd, row_counts={"customers": 0, "orders": 0})
    assert data == {"customers": [], "orders": []}


# --- Referential integrity (review P0.2) --------------------------------------------------------

def test_empty_parent_with_children_is_reported(small_erd):
    with pytest.raises(ContractError, match="Parent table customers has no rows"):
        _generate(small_erd, row_counts={"customers": 0})


def test_self_reference_before_its_key_group_is_reported():
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
        row_count: 5
        column_groups:
          - {name: boss, columns: [BOSS], generator: foreign_key, params: {parent: emp, parent_columns: [ID]}}
          - {name: key, columns: [ID], generator: sequence}
""")
    with pytest.raises(ContractError, match=r"needs \['ID'\] generated first"):
        generate_dataset(contract, schema, seed=1)


LINES_ERD = """erDiagram
    orders ||--|{ lines : "ORDERNUMBER=ORDERNUMBER"
    products ||--o{ lines : "PRODUCTCODE=PRODUCTCODE"
    orders {
        bigint ORDERNUMBER PK
    }
    products {
        string PRODUCTCODE PK
    }
    lines {
        bigint ORDERNUMBER PK, FK
        string PRODUCTCODE PK, FK
    }
"""


def _lines_contract(orders=10, products=4, lines=30, extra=""):
    return parse_contract(f"""
database: demo
contracts:
  - name: o
    table: orders
    policies:
      - name: p
        intent: FUNCTIONAL
        row_count: {orders}
        column_groups:
          - {{name: key, columns: [ORDERNUMBER], generator: sequence}}
  - name: pr
    table: products
    policies:
      - name: p
        intent: FUNCTIONAL
        row_count: {products}
        column_groups:
          - {{name: key, columns: [PRODUCTCODE], generator: sequence, params: {{prefix: S}}}}
  - name: l
    table: lines
    policies:
      - name: p
        intent: FUNCTIONAL
        row_count: {lines}
        column_groups:
          - name: keys
            columns: [ORDERNUMBER, PRODUCTCODE]
            generator: foreign_key
            params:
              parents: {{ORDERNUMBER: {{parent: orders, parent_columns: [ORDERNUMBER]}}, PRODUCTCODE: {{parent: products, parent_columns: [PRODUCTCODE]}}}}
              unique_together: true
              {extra}
""")


def test_multi_parent_keys_reference_both_parents_and_are_unique():
    data = generate_dataset(_lines_contract(), parse_erd(LINES_ERD), seed=3)
    orders = {r["ORDERNUMBER"] for r in data["orders"]}
    products = {r["PRODUCTCODE"] for r in data["products"]}
    pairs = [(r["ORDERNUMBER"], r["PRODUCTCODE"]) for r in data["lines"]]
    assert len(pairs) == 30 and len(set(pairs)) == 30
    assert all(o in orders and p in products for o, p in pairs)


def test_multi_parent_keys_can_use_every_combination():
    data = generate_dataset(_lines_contract(lines=40), parse_erd(LINES_ERD), seed=3)
    assert len({(r["ORDERNUMBER"], r["PRODUCTCODE"]) for r in data["lines"]}) == 40


def test_multi_parent_keys_are_deterministic():
    run = lambda seed: generate_dataset(_lines_contract(), parse_erd(LINES_ERD), seed=seed)["lines"]
    assert run(5) == run(5) and run(5) != run(6)


def test_multi_parent_keys_reject_more_rows_than_combinations():
    with pytest.raises(ContractError, match="only 40 combinations exist"):
        generate_dataset(_lines_contract(lines=41), parse_erd(LINES_ERD), seed=3)


def test_multi_parent_keys_report_empty_parent():
    with pytest.raises(ContractError, match="Parent table products has no rows"):
        generate_dataset(_lines_contract(products=0), parse_erd(LINES_ERD), seed=3)


def test_multi_parent_keys_report_missing_parent_spec():
    contract = _lines_contract()
    group = contract.contracts[2].policies[0].column_groups[0]
    del group.params["parents"]["PRODUCTCODE"]
    with pytest.raises(ContractError, match=r"missing \['PRODUCTCODE'\]"):
        generate_dataset(contract, parse_erd(LINES_ERD), seed=3)


def test_multi_parent_keys_reject_null_ratio():
    with pytest.raises(ContractError, match="null_ratio is not supported"):
        generate_dataset(_lines_contract(extra="null_ratio: 0.5"), parse_erd(LINES_ERD), seed=3)


def test_multi_parent_keys_reject_composite_parent_keys():
    contract = _lines_contract()
    spec = contract.contracts[2].policies[0].column_groups[0].params["parents"]["ORDERNUMBER"]
    spec["parent_columns"] = ["ORDERNUMBER", "OTHER"]
    with pytest.raises(ContractError, match="composite parent keys are not supported"):
        generate_dataset(contract, parse_erd(LINES_ERD), seed=3)


def test_multi_parent_keys_do_not_materialise_the_cartesian_product():
    import tracemalloc

    tracemalloc.start()
    data = generate_dataset(
        _lines_contract(orders=20_000, products=5_000, lines=1_000), parse_erd(LINES_ERD), seed=1
    )
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    assert len(data["lines"]) == 1_000
    # 100M combinations would need many GB if materialised.
    assert peak < 100 * 1024 * 1024
