import statistics

import pytest

from tdf.profiling import METRICS, VALUE_SET_CAP, profile_table

pytestmark = pytest.mark.req("FR-PROF-02", "FR-PROF-03")


def _obs(result, metric, column):
    (match,) = [o for o in result.observations if o.metric == metric and o.columns == [column]]
    return match.value


def test_metric_catalogue_is_complete():
    assert set(METRICS) == {
        "row_count", "null_count", "non_null_count", "distinct_non_null_count",
        "min", "max", "mean", "stddev", "value_set", "value_frequencies",
    }


def test_counts(small_connection):
    result = profile_table(small_connection, "customers")
    assert _obs(result, "row_count", "CUSTOMERNUMBER") == 4
    assert _obs(result, "null_count", "STATE") == 2
    assert _obs(result, "non_null_count", "STATE") == 2
    assert _obs(result, "distinct_non_null_count", "CITY") == 3


def test_numeric_summary(small_connection):
    result = profile_table(small_connection, "customers")
    assert _obs(result, "min", "CREDITLIMIT") == 100
    assert _obs(result, "max", "CREDITLIMIT") == 300
    assert _obs(result, "mean", "CREDITLIMIT") == pytest.approx(200.0)
    assert _obs(result, "stddev", "CREDITLIMIT") == pytest.approx(statistics.stdev([100, 200, 300]))


def test_value_set_and_frequencies_for_bounded_column(small_connection):
    result = profile_table(small_connection, "orders")
    assert set(_obs(result, "value_set", "STATUS")) == {"Shipped", "Cancelled", "On Hold"}
    assert _obs(result, "value_frequencies", "STATUS") == {"Shipped": 3, "Cancelled": 1, "On Hold": 1}


def test_no_value_set_for_unbounded_column(small_connection):
    result = profile_table(small_connection, "orders", columns=["ORDERNUMBER"])
    assert not [o for o in result.observations if o.metric in ("value_set", "value_frequencies")]
    assert VALUE_SET_CAP == 100


def test_every_observation_names_metric_column_and_segment(small_connection):
    result = profile_table(small_connection, "orders")
    assert result.table == "orders"
    assert result.observations
    for o in result.observations:
        assert o.metric in METRICS
        assert o.columns
        assert o.segment == "ALL"


def test_multi_column_value_set(small_connection):
    result = profile_table(
        small_connection, "customers", tuple_sets=[["CITY", "STATE", "COUNTRY"]]
    )
    (obs,) = [o for o in result.observations if len(o.columns) == 3]
    assert obs.metric == "value_set"
    combos = {tuple(v) for v in obs.value}
    assert combos == {
        ("Sydney", None, "Australia"), ("Boston", "MA", "USA"), ("Paris", None, "France"),
    }


def test_each_profile_run_has_a_distinct_id(small_connection):
    first = profile_table(small_connection, "orders")
    second = profile_table(small_connection, "orders")
    assert first.id != second.id
    assert first.created_at <= second.created_at


@pytest.mark.duckdb
@pytest.mark.req("AC-03")
def test_steelwheels_status_is_bounded_and_skewed(steelwheels_connection):
    result = profile_table(steelwheels_connection, "orders", columns=["STATUS"])
    freq = _obs(result, "value_frequencies", "STATUS")
    assert len(freq) == 6
    assert freq["Shipped"] == 307


def test_value_set_columns_opt_in_above_the_cap(small_connection):
    result = profile_table(small_connection, "orders", value_set_columns=["STATUS"])
    assert set(_obs(result, "value_set", "STATUS")) == {"Shipped", "Cancelled", "On Hold"}


def test_value_set_opt_in_is_per_column(small_connection):
    result = profile_table(small_connection, "customers", value_set_columns=["CUSTOMERNAME"])
    names = [o.columns for o in result.observations if o.metric == "value_set"]
    assert ["CUSTOMERNAME"] in names
    assert ["CUSTOMERNUMBER"] not in names
