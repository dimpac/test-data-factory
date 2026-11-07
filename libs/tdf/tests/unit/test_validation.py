import csv
from pathlib import Path

import pytest

from tdf.contracts import ExpectationSpec, Target
from tdf.metadata import parse_erd
from tdf.validation import Outcome, validate_dataset

pytestmark = pytest.mark.req("FR-VAL-01", "FR-VAL-02", "FR-VAL-04", "AC-09")


def _write(directory: Path, name: str, columns, rows):
    with open(directory / f"{name}.csv", "w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(columns)
        writer.writerows(rows)


@pytest.fixture
def dataset(tmp_path):
    _write(tmp_path, "customers", ["CUSTOMERNUMBER", "CUSTOMERNAME", "CITY", "STATE", "COUNTRY"],
           [[1, "A", "Boston", "MA", "USA"], [2, "B", "Paris", "", "France"]])
    _write(tmp_path, "orders", ["ORDERNUMBER", "STATUS", "CUSTOMERNUMBER"],
           [[10, "Shipped", 1], [11, "Cancelled", 2]])
    return tmp_path


def _exp(id, type, table, columns, scope="COLUMN", **params):
    return ExpectationSpec(id=id, type=type, scope=scope, target=Target(table=table, columns=columns), params=params)


def _run(dataset, small_erd, *expectations):
    results = validate_dataset(dataset, parse_erd(small_erd), list(expectations))
    return {r.expectation_id: r for r in results}


def test_satisfied_expectations(dataset, small_erd):
    results = _run(
        dataset, small_erd,
        _exp("u", "uniqueness", "orders", ["ORDERNUMBER"]),
        _exp("fk", "referential_integrity", "orders", ["CUSTOMERNUMBER"], "RELATIONSHIP",
             parent="customers", parent_columns=["CUSTOMERNUMBER"]),
        _exp("e", "enumeration", "orders", ["STATUS"], values=["Shipped", "Cancelled"]),
        _exp("v", "volume", "orders", [], "TABLE", min=1, max=5),
    )
    assert {r.outcome for r in results.values()} == {Outcome.SATISFIED}


def test_duplicate_key_is_an_unexpected_violation_with_evidence(dataset, small_erd):
    _write(dataset, "orders", ["ORDERNUMBER", "STATUS", "CUSTOMERNUMBER"], [[10, "Shipped", 1], [10, "Shipped", 2]])
    result = _run(dataset, small_erd, _exp("u", "uniqueness", "orders", ["ORDERNUMBER"]))["u"]
    assert result.outcome is Outcome.UNEXPECTED_VIOLATION
    assert "10" in result.evidence


def test_dangling_foreign_key_is_detected(dataset, small_erd):
    _write(dataset, "orders", ["ORDERNUMBER", "STATUS", "CUSTOMERNUMBER"], [[10, "Shipped", 999]])
    result = _run(
        dataset, small_erd,
        _exp("fk", "referential_integrity", "orders", ["CUSTOMERNUMBER"], "RELATIONSHIP",
             parent="customers", parent_columns=["CUSTOMERNUMBER"]),
    )["fk"]
    assert result.outcome is Outcome.UNEXPECTED_VIOLATION
    assert "999" in result.evidence


def test_null_foreign_key_is_not_a_violation(dataset, small_erd):
    _write(dataset, "orders", ["ORDERNUMBER", "STATUS", "CUSTOMERNUMBER"], [[10, "Shipped", ""]])
    result = _run(
        dataset, small_erd,
        _exp("fk", "referential_integrity", "orders", ["CUSTOMERNUMBER"], "RELATIONSHIP",
             parent="customers", parent_columns=["CUSTOMERNUMBER"]),
    )["fk"]
    assert result.outcome is Outcome.SATISFIED


def test_completeness_violation(dataset, small_erd):
    _write(dataset, "orders", ["ORDERNUMBER", "STATUS", "CUSTOMERNUMBER"], [[10, "", 1]])
    result = _run(dataset, small_erd, _exp("c", "completeness", "orders", ["STATUS"], max_null_ratio=0.0))["c"]
    assert result.outcome is Outcome.UNEXPECTED_VIOLATION


def test_range_violation(dataset, small_erd):
    result = _run(dataset, small_erd, _exp("r", "range", "orders", ["ORDERNUMBER"], min=100, max=200))["r"]
    assert result.outcome is Outcome.UNEXPECTED_VIOLATION


def test_enumeration_violation(dataset, small_erd):
    result = _run(dataset, small_erd, _exp("e", "enumeration", "orders", ["STATUS"], values=["Shipped"]))["e"]
    assert result.outcome is Outcome.UNEXPECTED_VIOLATION
    assert "Cancelled" in result.evidence


def test_volume_violation(dataset, small_erd):
    result = _run(dataset, small_erd, _exp("v", "volume", "orders", [], "TABLE", min=10, max=20))["v"]
    assert result.outcome is Outcome.UNEXPECTED_VIOLATION


@pytest.mark.req("AC-05")
def test_tuple_in_set_detects_inconsistent_combination(dataset, small_erd):
    _write(dataset, "customers", ["CUSTOMERNUMBER", "CUSTOMERNAME", "CITY", "STATE", "COUNTRY"],
           [[1, "A", "Boston", "MA", "USA"], [2, "B", "Paris", "MA", "USA"]])
    result = _run(
        dataset, small_erd,
        _exp("t", "tuple_in_set", "customers", ["CITY", "STATE", "COUNTRY"],
             values=[["Boston", "MA", "USA"], ["Paris", None, "France"]]),
    )["t"]
    assert result.outcome is Outcome.UNEXPECTED_VIOLATION
    assert "Paris" in result.evidence


@pytest.mark.req("AC-05")
def test_tuple_in_set_accepts_observed_combinations_with_nulls(dataset, small_erd):
    result = _run(
        dataset, small_erd,
        _exp("t", "tuple_in_set", "customers", ["CITY", "STATE", "COUNTRY"],
             values=[["Boston", "MA", "USA"], ["Paris", None, "France"]]),
    )["t"]
    assert result.outcome is Outcome.SATISFIED


def test_unknown_expectation_type_is_unevaluated(dataset, small_erd):
    result = _run(dataset, small_erd, _exp("x", "statistical_drift", "orders", ["ORDERNUMBER"]))["x"]
    assert result.outcome is Outcome.UNEVALUATED


def test_expected_violation_is_reported_as_expected(dataset, small_erd):
    _write(dataset, "orders", ["ORDERNUMBER", "STATUS", "CUSTOMERNUMBER"], [[10, "Shipped", 1], [10, "Shipped", 2]])
    expectation = _exp("u", "uniqueness", "orders", ["ORDERNUMBER"], expect_violation=True)
    assert _run(dataset, small_erd, expectation)["u"].outcome is Outcome.EXPECTED_VIOLATION


def test_validation_module_does_not_import_generators():
    import ast
    import inspect

    import tdf.validation.validator as module

    imported = {
        n.module for n in ast.walk(ast.parse(inspect.getsource(module)))
        if isinstance(n, ast.ImportFrom) and n.module
    } | {
        a.name for n in ast.walk(ast.parse(inspect.getsource(module)))
        if isinstance(n, ast.Import) for a in n.names
    }
    assert not any(name.startswith(("tdf.generators", "tdf.engine")) for name in imported)


def test_one_result_per_expectation(dataset, small_erd):
    results = validate_dataset(
        dataset, parse_erd(small_erd),
        [_exp("a", "uniqueness", "orders", ["ORDERNUMBER"]), _exp("b", "volume", "orders", [], "TABLE", min=0, max=9)],
    )
    assert [r.expectation_id for r in results] == ["a", "b"]


# --- Misconfigured expectations never pass silently (review P0.3) -------------------------------

@pytest.mark.parametrize("type_, params", [
    ("completeness", {}),
    ("uniqueness", {}),
    ("enumeration", {"values": ["Shipped"]}),
    ("range", {"min": 0}),
    ("tuple_in_set", {"values": [["Shipped"]]}),
])
def test_unknown_column_is_a_configuration_error(dataset, small_erd, type_, params):
    result = _run(dataset, small_erd, _exp("x", type_, "orders", ["NOPE"], **params))["x"]
    assert result.outcome is Outcome.UNEXPECTED_VIOLATION
    assert "configuration error" in result.evidence and "NOPE" in result.evidence


def test_missing_data_file_is_a_configuration_error(dataset, small_erd):
    result = _run(dataset, small_erd, _exp("x", "volume", "missing", [], scope="TABLE", min=1))["x"]
    assert result.outcome is Outcome.UNEXPECTED_VIOLATION
    assert "no data file missing.csv" in result.evidence


def test_referential_integrity_without_parent_is_a_configuration_error(dataset, small_erd):
    result = _run(dataset, small_erd, _exp("x", "referential_integrity", "orders", ["CUSTOMERNUMBER"],
                                           scope="RELATIONSHIP"))["x"]
    assert result.outcome is Outcome.UNEXPECTED_VIOLATION and "parent" in result.evidence


def test_referential_integrity_with_unknown_parent_column_is_a_configuration_error(dataset, small_erd):
    result = _run(dataset, small_erd, _exp("x", "referential_integrity", "orders", ["CUSTOMERNUMBER"],
                                           scope="RELATIONSHIP", parent="customers",
                                           parent_columns=["NOPE"]))["x"]
    assert result.outcome is Outcome.UNEXPECTED_VIOLATION and "NOPE" in result.evidence


def test_enumeration_without_values_is_a_configuration_error(dataset, small_erd):
    result = _run(dataset, small_erd, _exp("x", "enumeration", "orders", ["STATUS"], source="profile"))["x"]
    assert result.outcome is Outcome.UNEXPECTED_VIOLATION and "values" in result.evidence


def test_non_numeric_value_violates_numeric_range(dataset, small_erd):
    result = _run(dataset, small_erd, _exp("x", "range", "orders", ["STATUS"], min=0))["x"]
    assert result.outcome is Outcome.UNEXPECTED_VIOLATION and "Shipped" in result.evidence


def test_unapproved_expectations_are_not_evaluated(dataset, small_erd):
    rejected = ExpectationSpec(id="x", type="volume", scope="TABLE", target=Target(table="orders"),
                               params={"min": 100}, status="REJECTED")
    result = _run(dataset, small_erd, rejected)["x"]
    assert result.outcome is Outcome.UNEVALUATED and "REJECTED" in result.evidence


def test_unsupported_type_explains_why_it_is_unevaluated(dataset, small_erd):
    result = _run(dataset, small_erd, _exp("x", "regex", "orders", ["STATUS"]))["x"]
    assert result.outcome is Outcome.UNEVALUATED and "unsupported" in result.evidence
