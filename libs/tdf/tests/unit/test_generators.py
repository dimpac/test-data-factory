import pytest

from tdf.generators import UnknownGeneratorError, available_generators, get_generator
from tdf.profiling import Observation, ProfileResult

pytestmark = pytest.mark.req("FR-GEN-01")

REQUIRED = {
    "sequence", "integer", "float", "string", "boolean", "date", "timestamp",
    "categorical", "tuple", "foreign_key",
}


def _run(name, *, count=200, seed=42, columns=("C",), params=None, profile=None):
    return get_generator(name).generate(
        count=count, seed=seed, columns=list(columns), params=params or {}, profile=profile
    )


def _profile(*observations):
    from datetime import datetime

    return ProfileResult(id="p1", table="t", created_at=datetime(2026, 1, 1), observations=list(observations))


def test_required_generators_are_registered():
    assert REQUIRED <= available_generators()


def test_unknown_generator_raises():
    with pytest.raises(UnknownGeneratorError):
        get_generator("telepathy")


@pytest.mark.parametrize("name", sorted(REQUIRED - {"categorical", "tuple", "foreign_key"}))
@pytest.mark.req("AC-02")
def test_same_seed_gives_identical_output(name):
    assert _run(name, seed=7) == _run(name, seed=7)


@pytest.mark.parametrize("name", ["integer", "float", "string"])
def test_different_seed_gives_different_output(name):
    assert _run(name, seed=1) != _run(name, seed=2)


@pytest.mark.req("FR-GEN-02")
def test_integer_respects_range_and_type():
    rows = _run("integer", params={"min": 5, "max": 9})
    assert len(rows) == 200
    assert all(isinstance(r["C"], int) and 5 <= r["C"] <= 9 for r in rows)


@pytest.mark.req("FR-GEN-02", "FR-GEN-06")
def test_float_respects_range_and_type():
    rows = _run("float", params={"min": 0.0, "max": 1.0})
    assert all(isinstance(r["C"], float) and 0.0 <= r["C"] <= 1.0 for r in rows)


@pytest.mark.req("FR-GEN-02")
def test_string_boolean_date_timestamp_types():
    import datetime as dt

    assert all(isinstance(r["C"], str) for r in _run("string"))
    assert all(isinstance(r["C"], bool) for r in _run("boolean"))
    assert all(type(r["C"]) is dt.date for r in _run("date", params={"start": "2020-01-01", "end": "2020-12-31"}))
    assert all(isinstance(r["C"], dt.datetime) for r in _run("timestamp", params={"start": "2020-01-01", "end": "2020-12-31"}))


def test_sequence_is_unique_and_ordered():
    rows = _run("sequence", count=5, params={"start": 100})
    assert [r["C"] for r in rows] == [100, 101, 102, 103, 104]


@pytest.mark.req("FR-GEN-04")
def test_null_ratio_is_within_tolerance():
    rows = _run("integer", count=2000, params={"min": 0, "max": 9, "null_ratio": 0.25})
    nulls = sum(r["C"] is None for r in rows)
    assert nulls / 2000 == pytest.approx(0.25, abs=0.04)


@pytest.mark.req("FR-GEN-05")
def test_categorical_from_declared_values_only():
    rows = _run("categorical", params={"values": ["a", "b", "c"]})
    assert {r["C"] for r in rows} <= {"a", "b", "c"}


@pytest.mark.req("AC-03", "FR-GEN-05")
def test_categorical_reproduces_profile_frequencies_within_tolerance():
    profile = _profile(
        Observation(metric="value_frequencies", columns=["C"], value={"Shipped": 307, "Cancelled": 6, "On Hold": 4, "Disputed": 3})
    )
    rows = _run("categorical", count=4000, params={"source": "profile"}, profile=profile)
    counts = {}
    for r in rows:
        counts[r["C"]] = counts.get(r["C"], 0) + 1
    assert set(counts) <= {"Shipped", "Cancelled", "On Hold", "Disputed"}
    total = 307 + 6 + 4 + 3
    for value, observed in {"Shipped": 307, "Cancelled": 6, "On Hold": 4, "Disputed": 3}.items():
        assert counts.get(value, 0) / 4000 == pytest.approx(observed / total, abs=0.02)


@pytest.mark.req("AC-03")
def test_profile_driven_categorical_is_deterministic():
    profile = _profile(Observation(metric="value_frequencies", columns=["C"], value={"a": 3, "b": 1}))
    first = _run("categorical", params={"source": "profile"}, profile=profile, seed=3)
    second = _run("categorical", params={"source": "profile"}, profile=profile, seed=3)
    assert first == second


@pytest.mark.req("AC-03")
def test_profile_driven_categorical_without_profile_is_an_error():
    with pytest.raises(ValueError, match="profile"):
        _run("categorical", params={"source": "profile"})


@pytest.mark.req("AC-05", "FR-GEN-07")
def test_tuple_generator_emits_only_observed_combinations():
    observed = [["Sydney", None, "Australia"], ["Boston", "MA", "USA"], ["Paris", None, "France"]]
    profile = _profile(Observation(metric="value_set", columns=["CITY", "STATE", "COUNTRY"], value=observed))
    rows = _run("tuple", columns=("CITY", "STATE", "COUNTRY"), profile=profile, params={"source": "profile"})
    assert rows
    allowed = {tuple(v) for v in observed}
    assert {(r["CITY"], r["STATE"], r["COUNTRY"]) for r in rows} <= allowed
    assert len({(r["CITY"], r["STATE"], r["COUNTRY"]) for r in rows}) > 1


@pytest.mark.req("AC-05")
def test_tuple_generator_is_deterministic():
    observed = [["Sydney", None, "Australia"], ["Boston", "MA", "USA"]]
    profile = _profile(Observation(metric="value_set", columns=["CITY", "STATE", "COUNTRY"], value=observed))
    run = lambda: _run("tuple", columns=("CITY", "STATE", "COUNTRY"), profile=profile, params={"source": "profile"}, seed=9)
    assert run() == run()


@pytest.mark.req("AC-05")
def test_unique_tuple_generation_never_repeats_an_observed_combination():
    observed = [["NA", "US", "1"], ["EMEA", "UK", "2"], ["APAC", "AU", "3"]]
    profile = _profile(Observation(metric="value_set", columns=["TERRITORY", "COUNTRY", "CODE"], value=observed))
    rows = _run("tuple", count=3, columns=("TERRITORY", "COUNTRY", "CODE"), profile=profile,
                params={"source": "profile", "unique": True})
    assert sorted(tuple(r.values()) for r in rows) == sorted(tuple(v) for v in observed)


@pytest.mark.req("AC-05")
def test_unique_tuple_generation_rejects_more_rows_than_combinations():
    observed = [["NA", "US", "1"]]
    profile = _profile(Observation(metric="value_set", columns=["TERRITORY", "COUNTRY", "CODE"], value=observed))
    with pytest.raises(ValueError, match="combinations"):
        _run("tuple", count=2, columns=("TERRITORY", "COUNTRY", "CODE"), profile=profile,
             params={"source": "profile", "unique": True})


@pytest.mark.req("FR-GEN-01")
def test_faker_generator_is_deterministic_and_uses_provider():
    first = _run("faker", count=20, seed=5, params={"provider": "name"})
    assert first == _run("faker", count=20, seed=5, params={"provider": "name"})
    assert all(isinstance(r["C"], str) and " " in r["C"] for r in first)


def test_faker_generator_requires_provider():
    with pytest.raises(ValueError, match="provider"):
        _run("faker", params={})


GEO_HEADER = "COUNTRY,POSTAL_CODE,CITY,STATE,SHORT_STATE\n"


@pytest.mark.req("FR-GEN-01")
def test_geo_generator_keeps_city_state_postal_and_country_together(tmp_path):
    db = tmp_path / "postal.csv"
    db.write_text(GEO_HEADER + "US,94080,South San Francisco,California,CA\nFR,75017,Paris,Ile-de-France,IDF\n")
    rows = _run("geo", count=200, columns=("CITY", "STATE", "POSTALCODE", "COUNTRY"),
                params={"source": str(db), "countries": ["USA", "France"]})
    allowed = {
        ("South San Francisco", "CA", "94080", "USA"),
        ("Paris", "IDF", "75017", "France"),
    }
    assert {(r["CITY"], r["STATE"], r["POSTALCODE"], r["COUNTRY"]) for r in rows} <= allowed
    assert len({tuple(r.values()) for r in rows}) == 2


@pytest.mark.req("FR-GEN-01")
def test_geo_generator_is_deterministic(tmp_path):
    db = tmp_path / "postal.csv"
    db.write_text(GEO_HEADER + "US,94080,South San Francisco,California,CA\nUS,94002,Belmont,California,CA\n")
    run = lambda: _run("geo", count=10, seed=3, columns=("CITY", "STATE", "POSTALCODE", "COUNTRY"),
                       params={"source": str(db), "countries": ["USA"]})
    assert run() == run()
