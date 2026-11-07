import pytest

from tdf.metadata import check_schema, introspect_duckdb, parse_erd

pytestmark = pytest.mark.req("FR-META-05")


def test_introspect_reads_table_and_column_types(small_duckdb):
    physical = introspect_duckdb(small_duckdb)
    assert set(physical) == {"customers", "orders"}
    assert physical["orders"]["ORDERNUMBER"] == "BIGINT"
    assert physical["customers"]["CITY"] == "VARCHAR"


def test_matching_schema_has_no_issues(small_erd):
    physical = {
        "customers": {"CUSTOMERNUMBER": "BIGINT", "CUSTOMERNAME": "VARCHAR", "CITY": "VARCHAR",
                      "STATE": "VARCHAR", "COUNTRY": "VARCHAR"},
        "orders": {"ORDERNUMBER": "BIGINT", "STATUS": "VARCHAR", "CUSTOMERNUMBER": "BIGINT"},
    }
    assert check_schema(parse_erd(small_erd), physical) == []


def test_missing_column_is_an_error(small_erd):
    physical = {
        "customers": {"CUSTOMERNUMBER": "BIGINT", "CUSTOMERNAME": "VARCHAR", "CITY": "VARCHAR",
                      "STATE": "VARCHAR", "COUNTRY": "VARCHAR"},
        "orders": {"ORDERNUMBER": "BIGINT", "STATUS": "VARCHAR"},
    }
    issues = check_schema(parse_erd(small_erd), physical)
    errors = [i for i in issues if i.severity == "error"]
    assert len(errors) == 1
    assert "orders.CUSTOMERNUMBER" in errors[0].message


def test_missing_table_is_an_error(small_erd):
    issues = check_schema(parse_erd(small_erd), {"customers": {}})
    assert any(i.severity == "error" and "orders" in i.message for i in issues)


def test_type_mismatch_is_only_a_warning(small_erd):
    physical = {
        "customers": {"CUSTOMERNUMBER": "VARCHAR", "CUSTOMERNAME": "VARCHAR", "CITY": "VARCHAR",
                      "STATE": "VARCHAR", "COUNTRY": "VARCHAR"},
        "orders": {"ORDERNUMBER": "BIGINT", "STATUS": "VARCHAR", "CUSTOMERNUMBER": "BIGINT"},
    }
    issues = check_schema(parse_erd(small_erd), physical)
    assert [i.severity for i in issues] == ["warning"]
    assert "customers.CUSTOMERNUMBER" in issues[0].message


@pytest.mark.duckdb
def test_normalised_steelwheels_erd_matches_physical_columns():
    from ..conftest import STEELWHEELS_DB, STEELWHEELS_ERD
    from tdf.metadata import load_erd

    issues = check_schema(load_erd(STEELWHEELS_ERD), introspect_duckdb(STEELWHEELS_DB))
    assert [i for i in issues if i.severity == "error"] == []
