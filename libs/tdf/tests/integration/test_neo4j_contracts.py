import pytest

from tdf.contracts import load_contract_file
from tdf.metadata import MetadataRepository, introspect_duckdb, load_erd

from ..conftest import STEELWHEELS_CONTRACT, STEELWHEELS_DB, STEELWHEELS_ERD

pytestmark = [pytest.mark.neo4j, pytest.mark.duckdb, pytest.mark.req("FR-CON-01", "FR-CON-04", "FR-CON-05", "FR-CON-06")]


@pytest.fixture
def repo(graph):
    repository = MetadataRepository(graph)
    repository.register_database("steelwheels", load_erd(STEELWHEELS_ERD), introspect_duckdb(STEELWHEELS_DB))
    for contract in load_contract_file(STEELWHEELS_CONTRACT).contracts:
        repository.save_contract("steelwheels", contract)
    return repository


def test_contract_graph_follows_the_ontology(graph, repo):
    rows = graph.run(
        "MATCH (:Table {name:'orders'})-[:HAS_GENERATOR_CONTRACT]->(c:GeneratorContract)"
        "-[:HAS_POLICY]->(p:GenerationPolicy)-[:HAS_COLUMN_GROUP]->(g:ColumnGroup)-[:INCLUDES]->(col:Column) "
        "RETURN c.version AS version, p.intent AS intent, g.name AS grp, col.name AS col"
    )
    assert rows and {r["intent"] for r in rows} == {"FUNCTIONAL"}
    assert {r["version"] for r in rows} == {1}
    assert {r["col"] for r in rows} >= {"ORDERNUMBER", "STATUS", "CUSTOMERNUMBER"}


def test_column_groups_use_generators(graph, repo):
    rows = graph.run(
        "MATCH (:ColumnGroup {name:'status'})-[:USES_GENERATOR]->(g:Generator) RETURN DISTINCT g.name AS name"
    )
    assert [r["name"] for r in rows] == ["categorical"]


def test_policies_enforce_expectations(graph, repo):
    rows = graph.run(
        "MATCH (:GenerationPolicy {name:'orders_functional'})-[:ENFORCES]->(e:Expectation) "
        "RETURN e.id AS id, e.source AS source, e.status AS status, e.scope AS scope"
    )
    assert {r["id"] for r in rows} == {"orders_pk_unique", "orders_status_enum", "orders_customer_fk"}
    assert {r["source"] for r in rows} == {"DECLARED"} and {r["status"] for r in rows} == {"APPROVED"}


def test_contract_round_trips(repo):
    original = {c.table: c for c in load_contract_file(STEELWHEELS_CONTRACT).contracts}
    loaded = repo.load_contract("steelwheels", "orders")
    assert loaded == original["orders"]


def test_saving_a_contract_twice_does_not_duplicate_nodes(graph, repo):
    before = graph.run("MATCH (n) RETURN count(n) AS n")[0]["n"]
    for contract in load_contract_file(STEELWHEELS_CONTRACT).contracts:
        repo.save_contract("steelwheels", contract)
    assert graph.run("MATCH (n) RETURN count(n) AS n")[0]["n"] == before
