import pytest

from tdf.metadata import ErdParseError, load_erd, parse_erd

from ..conftest import STEELWHEELS_ERD

pytestmark = pytest.mark.req("FR-META-02", "FR-META-03", "FR-META-04")


def test_small_erd_tables_and_columns(small_erd):
    schema = parse_erd(small_erd)
    assert set(schema.tables) == {"customers", "orders"}
    cols = {c.name: c for c in schema.tables["orders"].columns}
    assert list(cols) == ["ORDERNUMBER", "STATUS", "CUSTOMERNUMBER"]
    assert cols["ORDERNUMBER"].primary_key and not cols["ORDERNUMBER"].foreign_key
    assert cols["CUSTOMERNUMBER"].foreign_key and cols["CUSTOMERNUMBER"].type == "bigint"


def test_relationship_direction_and_join_columns(small_erd):
    (rel,) = parse_erd(small_erd).relationships
    assert (rel.parent, rel.child) == ("customers", "orders")
    assert rel.parent_columns == ["CUSTOMERNUMBER"]
    assert rel.child_columns == ["CUSTOMERNUMBER"]
    assert rel.cardinality == "one_to_many"
    assert rel.optional is False


def test_steelwheels_erd_has_six_tables_and_six_relationships():
    schema = load_erd(STEELWHEELS_ERD)
    assert set(schema.tables) == {
        "customers", "orders", "orderdetails", "products", "employees", "offices",
    }
    assert len(schema.relationships) == 6


def test_steelwheels_composite_primary_key():
    schema = load_erd(STEELWHEELS_ERD)
    pk = [c.name for c in schema.tables["orderdetails"].columns if c.primary_key]
    assert pk == ["ORDERNUMBER", "PRODUCTCODE"]


def test_steelwheels_optional_sales_rep_relationship():
    schema = load_erd(STEELWHEELS_ERD)
    rel = next(
        r for r in schema.relationships
        if (r.parent, r.child) == ("employees", "customers")
    )
    assert rel.parent_columns == ["EMPLOYEENUMBER"]
    assert rel.child_columns == ["SALESREPEMPLOYEENUMBER"]
    assert rel.optional is True


def test_steelwheels_self_reference_is_parsed():
    schema = load_erd(STEELWHEELS_ERD)
    rel = next(r for r in schema.relationships if r.parent == r.child == "employees")
    assert rel.child_columns == ["REPORTSTO"]
    assert rel.optional is True


def test_steelwheels_names_are_normalised():
    schema = load_erd(STEELWHEELS_ERD)
    assert "REQUIREDDATE" in {c.name for c in schema.tables["orders"].columns}
    assert "SALESREPEMPLOYEENUMBER" in {c.name for c in schema.tables["customers"].columns}


def test_composite_join_label():
    text = """erDiagram
    a ||--o{ b : "X=X,Y=Y"
    a {
        int X PK
        int Y PK
    }
    b {
        int X FK
        int Y FK
    }
"""
    (rel,) = parse_erd(text).relationships
    assert rel.parent_columns == ["X", "Y"]
    assert rel.child_columns == ["X", "Y"]


def test_relationship_without_join_columns_is_an_error():
    text = 'erDiagram\n    a ||--o{ b : ""\n    a {\n        int X PK\n    }\n    b {\n        int X FK\n    }\n'
    with pytest.raises(ErdParseError, match="join"):
        parse_erd(text)


def test_relationship_naming_unknown_column_is_an_error():
    text = 'erDiagram\n    a ||--o{ b : "X=NOPE"\n    a {\n        int X PK\n    }\n    b {\n        int X FK\n    }\n'
    with pytest.raises(ErdParseError, match="NOPE"):
        parse_erd(text)


def test_relationship_naming_unknown_table_is_an_error():
    text = 'erDiagram\n    a ||--o{ ghost : "X=X"\n    a {\n        int X PK\n    }\n'
    with pytest.raises(ErdParseError, match="ghost"):
        parse_erd(text)
