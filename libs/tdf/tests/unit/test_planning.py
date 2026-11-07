import pytest

from tdf.metadata import Column, Relationship, SchemaModel, Table, load_erd
from tdf.planning import DependencyCycleError, generation_order

from ..conftest import STEELWHEELS_ERD

pytestmark = pytest.mark.req("FR-META-06", "FR-GEN-09", "AC-07")


def _schema(tables, edges):
    return SchemaModel(
        tables={t: Table(name=t, columns=[Column(name="ID", type="int")]) for t in tables},
        relationships=[
            Relationship(parent=p, child=c, parent_columns=["ID"], child_columns=["ID"])
            for p, c in edges
        ],
    )


def test_parents_come_before_children():
    order = generation_order(_schema(["c", "b", "a"], [("a", "b"), ("b", "c")]))
    assert order == ["a", "b", "c"]


def test_order_is_deterministic():
    schema = _schema(["z", "y", "x"], [])
    assert generation_order(schema) == generation_order(schema)


def test_steelwheels_order_respects_every_dependency():
    schema = load_erd(STEELWHEELS_ERD)
    order = generation_order(schema)
    assert sorted(order) == sorted(schema.tables)
    for rel in schema.relationships:
        if rel.parent != rel.child:
            assert order.index(rel.parent) < order.index(rel.child)


def test_self_reference_is_accepted():
    assert generation_order(_schema(["emp"], [("emp", "emp")])) == ["emp"]


def test_cycle_raises_actionable_error_naming_tables():
    schema = _schema(["a", "b", "c"], [("a", "b"), ("b", "c"), ("c", "a")])
    with pytest.raises(DependencyCycleError) as exc:
        generation_order(schema)
    message = str(exc.value)
    assert all(t in message for t in ("a", "b", "c"))
