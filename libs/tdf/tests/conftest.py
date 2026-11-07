"""Shared fixtures for the Test Data Factory tests."""

from __future__ import annotations

import os
import uuid
from pathlib import Path

import duckdb
import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
STEELWHEELS_DB = REPO_ROOT / "data" / "steelwheels.duckdb"
STEELWHEELS_ERD = REPO_ROOT / "docs" / "steelwheels_erd.mmd"
STEELWHEELS_CONTRACT = Path(__file__).resolve().parents[1] / "config" / "steelwheels" / "contract.yaml"
TEST_DATABASE = "tdf_test"

SMALL_ERD = """erDiagram
    customers ||--|{ orders : "CUSTOMERNUMBER=CUSTOMERNUMBER"
    customers {
        bigint CUSTOMERNUMBER PK
        string CUSTOMERNAME
        string CITY
        string STATE
        string COUNTRY
    }
    orders {
        bigint ORDERNUMBER PK
        string STATUS
        bigint CUSTOMERNUMBER FK
    }
"""


def pytest_collection_modifyitems(config, items):
    """Skip tests whose external dependency is unavailable."""
    for item in items:
        if item.get_closest_marker("duckdb") and not STEELWHEELS_DB.exists():
            item.add_marker(pytest.mark.skip(reason=f"{STEELWHEELS_DB} not found"))
        if item.get_closest_marker("neo4j") and not _neo4j_reachable():
            item.add_marker(pytest.mark.skip(reason="Neo4j is not reachable"))


def _neo4j_reachable() -> bool:
    import socket
    from urllib.parse import urlparse

    url = urlparse(os.environ.get("NEO4J_URL", "bolt://test-data-factory-graph:7687"))
    try:
        with socket.create_connection((url.hostname, url.port or 7687), timeout=2):
            return bool(os.environ.get("NEO4J_PASSWORD"))
    except OSError:
        return False


@pytest.fixture
def small_erd() -> str:
    return SMALL_ERD


@pytest.fixture
def small_duckdb(tmp_path: Path):
    """A tiny Customers/Orders database with known values."""
    path = tmp_path / "small.duckdb"
    with duckdb.connect(str(path)) as con:
        con.execute(
            "CREATE TABLE customers (CUSTOMERNUMBER BIGINT, CUSTOMERNAME VARCHAR, "
            "CITY VARCHAR, STATE VARCHAR, COUNTRY VARCHAR, CREDITLIMIT BIGINT)"
        )
        con.execute(
            "INSERT INTO customers VALUES "
            "(1,'A','Sydney',NULL,'Australia',100),"
            "(2,'B','Boston','MA','USA',200),"
            "(3,'C','Boston','MA','USA',300),"
            "(4,'D','Paris',NULL,'France',NULL)"
        )
        con.execute(
            "CREATE TABLE orders (ORDERNUMBER BIGINT, STATUS VARCHAR, CUSTOMERNUMBER BIGINT)"
        )
        con.execute(
            "INSERT INTO orders VALUES "
            "(10,'Shipped',1),(11,'Shipped',2),(12,'Shipped',2),(13,'Cancelled',3),(14,'On Hold',4)"
        )
    return path


@pytest.fixture
def small_connection(small_duckdb: Path):
    con = duckdb.connect(str(small_duckdb), read_only=True)
    yield con
    con.close()


@pytest.fixture
def steelwheels_connection():
    con = duckdb.connect(str(STEELWHEELS_DB), read_only=True)
    yield con
    con.close()


@pytest.fixture
def graph():
    """A GraphClient bound to a dedicated, wiped test database."""
    from tdf.graph import GraphClient

    client = GraphClient.from_env(database=TEST_DATABASE)
    client.run("MATCH (n) DETACH DELETE n")
    yield client
    client.run("MATCH (n) DETACH DELETE n")
    client.close()


@pytest.fixture
def unique_id() -> str:
    return uuid.uuid4().hex[:8]
