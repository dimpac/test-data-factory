"""P1 exit criterion: generate a reproducible, relationally consistent SteelWheels dataset from a
declared contract and validate it from the CLI."""

import hashlib
from pathlib import Path

import pytest
from click.testing import CliRunner

from tdf.cli import main

from ..conftest import REPO_ROOT, STEELWHEELS_CONTRACT, STEELWHEELS_DB, STEELWHEELS_ERD

pytestmark = [pytest.mark.neo4j, pytest.mark.duckdb]

TABLES = ["customers", "employees", "offices", "orderdetails", "orders", "products"]


@pytest.fixture
def pipeline(graph, monkeypatch):
    monkeypatch.setenv("NEO4J_DATABASE", "tdf-test")
    runner = CliRunner()

    def run(*args):
        result = runner.invoke(main, [str(a) for a in args])
        assert result.exit_code == 0, result.output
        return result

    run("metadata", "register", "--database", "steelwheels", "--erd", STEELWHEELS_ERD, "--source", STEELWHEELS_DB)
    # Contracts first: profiling emits the tuple sets the contracts declare.
    run("contract", "load", STEELWHEELS_CONTRACT)
    for table in TABLES:
        run("profile", "--database", "steelwheels", "--source", STEELWHEELS_DB, "--table", table)
    return run


def _digest(directory: Path) -> dict[str, str]:
    return {t: hashlib.sha256((directory / f"{t}.csv").read_bytes()).hexdigest() for t in TABLES}


@pytest.mark.req("AC-02")
def test_generation_is_reproducible(pipeline, tmp_path):
    first, second = tmp_path / "a", tmp_path / "b"
    pipeline("generate", "--database", "steelwheels", "--seed", 42, "--out", first)
    pipeline("generate", "--database", "steelwheels", "--seed", 42, "--out", second)
    assert _digest(first) == _digest(second)


@pytest.mark.req("AC-02")
def test_different_seed_gives_different_output(pipeline, tmp_path):
    first, second = tmp_path / "a", tmp_path / "b"
    pipeline("generate", "--database", "steelwheels", "--seed", 1, "--out", first)
    pipeline("generate", "--database", "steelwheels", "--seed", 2, "--out", second)
    assert _digest(first) != _digest(second)


@pytest.mark.req("AC-01", "AC-09")
def test_generated_dataset_validates(pipeline, tmp_path):
    pipeline("generate", "--database", "steelwheels", "--seed", 42, "--out", tmp_path)
    result = pipeline("validate", "--database", "steelwheels", "--data-dir", tmp_path)
    assert "UNEXPECTED_VIOLATION" not in result.output
    assert "SATISFIED" in result.output


@pytest.mark.req("AC-01")
def test_relationships_hold_in_generated_csvs(pipeline, tmp_path):
    import duckdb

    pipeline("generate", "--database", "steelwheels", "--seed", 42, "--out", tmp_path)
    con = duckdb.connect()
    for table in TABLES:
        con.execute(f"CREATE VIEW {table} AS SELECT * FROM read_csv('{tmp_path / table}.csv', header=true)")
    orphans = """
        SELECT (SELECT count(*) FROM orders o WHERE o.CUSTOMERNUMBER NOT IN (SELECT CUSTOMERNUMBER FROM customers))
             + (SELECT count(*) FROM orderdetails d WHERE d.ORDERNUMBER NOT IN (SELECT ORDERNUMBER FROM orders))
             + (SELECT count(*) FROM orderdetails d WHERE d.PRODUCTCODE NOT IN (SELECT PRODUCTCODE FROM products))
             + (SELECT count(*) FROM employees e WHERE e.OFFICECODE NOT IN (SELECT OFFICECODE FROM offices))
             + (SELECT count(*) FROM customers c WHERE c.SALESREPEMPLOYEENUMBER IS NOT NULL
                  AND c.SALESREPEMPLOYEENUMBER NOT IN (SELECT EMPLOYEENUMBER FROM employees))
             + (SELECT count(*) FROM employees e WHERE e.REPORTSTO IS NOT NULL
                  AND e.REPORTSTO NOT IN (SELECT EMPLOYEENUMBER FROM employees))
    """
    assert con.execute(orphans).fetchone()[0] == 0


@pytest.mark.req("AC-03")
def test_status_distribution_follows_the_profile(pipeline, tmp_path):
    import duckdb

    pipeline("generate", "--database", "steelwheels", "--seed", 42, "--out", tmp_path, "--rows", "orders=3000")
    con = duckdb.connect()
    share = con.execute(
        f"SELECT avg(CASE WHEN STATUS = 'Shipped' THEN 1.0 ELSE 0 END) "
        f"FROM read_csv('{tmp_path / 'orders.csv'}', header=true)"
    ).fetchone()[0]
    assert share == pytest.approx(307 / 330, abs=0.03)


@pytest.mark.req("AC-05")
def test_customer_locations_are_real_postal_records(pipeline, tmp_path):
    import csv

    from tdf.generators.registry import COUNTRY_CODES, _geo_pool

    pipeline("generate", "--database", "steelwheels", "--seed", 42, "--out", tmp_path)
    postal = {
        (city, state or None, code, country)
        for city, state, code, country in _geo_pool(str(REPO_ROOT / "data" / "allCountriesCSV.csv"), list(COUNTRY_CODES))
    }
    with open(tmp_path / "customers.csv", newline="") as handle:
        rows = list(csv.DictReader(handle))
    locations = {(r["CITY"], r["STATE"] or None, r["POSTALCODE"], r["COUNTRY"]) for r in rows}
    assert locations and locations <= postal
    # Geo draws are not limited to the seven locations present in the source.
    assert len(locations) > 7


@pytest.mark.req("AC-09")
def test_validation_reports_corruption_even_though_generation_succeeded(pipeline, tmp_path):
    pipeline("generate", "--database", "steelwheels", "--seed", 42, "--out", tmp_path)
    orders = tmp_path / "orders.csv"
    lines = orders.read_text().splitlines()
    header, first = lines[0].split(","), lines[1].split(",")
    first[header.index("CUSTOMERNUMBER")] = "99999999"
    orders.write_text("\n".join([lines[0], ",".join(first), *lines[2:]]) + "\n")
    result = CliRunner().invoke(main, ["validate", "--database", "steelwheels", "--data-dir", str(tmp_path)])
    assert result.exit_code != 0
    assert "UNEXPECTED_VIOLATION" in result.output and "99999999" in result.output


@pytest.mark.req("FR-GEN-10")
def test_row_counts_follow_the_contract(pipeline, tmp_path):
    pipeline("generate", "--database", "steelwheels", "--seed", 42, "--out", tmp_path)
    assert sum(1 for _ in open(tmp_path / "orders.csv")) - 1 == 330
    assert sum(1 for _ in open(tmp_path / "offices.csv")) - 1 == 7
