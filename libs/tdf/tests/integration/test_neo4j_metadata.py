import pytest

from tdf.metadata import MetadataRepository, introspect_duckdb, load_erd
from tdf.profiling import profile_table

from ..conftest import STEELWHEELS_DB, STEELWHEELS_ERD

pytestmark = [pytest.mark.neo4j, pytest.mark.duckdb]


@pytest.fixture
def repo(graph):
    repository = MetadataRepository(graph)
    repository.register_database("steelwheels", load_erd(STEELWHEELS_ERD), introspect_duckdb(STEELWHEELS_DB))
    return repository


@pytest.mark.req("FR-META-01")
def test_registration_creates_ontology_nodes(graph, repo):
    def count(label):
        return graph.run(f"MATCH (n:{label}) RETURN count(n) AS n")[0]["n"]

    assert count("Database") == 1 and count("Table") == 6
    assert count("Column") == 51  # 13 + 7 + 9 + 5 + 8 + 9 across the six tables
    assert graph.run("MATCH (:Database)-[r:HAS_TABLE]->(:Table) RETURN count(r) AS n")[0]["n"] == 6
    assert graph.run("MATCH (:Table)-[r:HAS_COLUMN]->(:Column) RETURN count(r) AS n")[0]["n"] == count("Column")


@pytest.mark.req("FR-META-01")
def test_registration_is_idempotent(graph, repo):
    before = graph.run("MATCH (n) RETURN count(n) AS n")[0]["n"]
    repo.register_database("steelwheels", load_erd(STEELWHEELS_ERD), introspect_duckdb(STEELWHEELS_DB))
    assert graph.run("MATCH (n) RETURN count(n) AS n")[0]["n"] == before


@pytest.mark.req("FR-META-04")
def test_relates_to_edges_carry_join_columns(repo):
    relationships = repo.get_relationships("steelwheels")
    assert len(relationships) == 6
    rep = next(r for r in relationships if (r.parent, r.child) == ("employees", "customers"))
    assert rep.child_columns == ["SALESREPEMPLOYEENUMBER"] and rep.optional is True
    assert any(r.parent == r.child == "employees" for r in relationships)


@pytest.mark.req("FR-META-01")
def test_schema_round_trips(repo):
    schema = repo.get_schema("steelwheels")
    assert set(schema.tables) == {"customers", "orders", "orderdetails", "products", "employees", "offices"}
    assert [c.name for c in schema.tables["orders"].columns][:2] == ["ORDERNUMBER", "ORDERDATE"]


@pytest.mark.req("FR-PROF-05", "FR-PROF-06", "AC-08")
def test_two_profiles_of_one_table_stay_distinct(repo, steelwheels_connection):
    first = repo.save_profile("steelwheels", profile_table(steelwheels_connection, "orders", columns=["STATUS"]))
    second = repo.save_profile("steelwheels", profile_table(steelwheels_connection, "orders", columns=["STATUS"]))
    assert first != second
    profiles = repo.list_profiles("steelwheels", "orders")
    assert {p["id"] for p in profiles} == {first, second}
    assert all(p["segment"] == "ALL" and p["created_at"] for p in profiles)


@pytest.mark.req("AC-08")
def test_observations_are_queryable_by_profile_and_segment(graph, repo, steelwheels_connection):
    pid = repo.save_profile("steelwheels", profile_table(steelwheels_connection, "orders", columns=["STATUS"]))
    rows = graph.run(
        "MATCH (p:DataProfile {id:$id})-[:HAS_SEGMENT]->(s:ProfileSegment)-[:HAS_OBSERVATION]->"
        "(o:ProfileObservation)-[:USES_METRIC]->(m:ProfileMetric) "
        "MATCH (o)-[:ABOUT]->(c:Column) RETURN s.name AS segment, m.name AS metric, c.name AS column",
        id=pid,
    )
    assert rows and {r["segment"] for r in rows} == {"ALL"}
    assert {"row_count", "value_frequencies"} <= {r["metric"] for r in rows}
    assert {r["column"] for r in rows} == {"STATUS"}


@pytest.mark.req("FR-PROF-05")
def test_profile_is_linked_to_its_table(graph, repo, steelwheels_connection):
    pid = repo.save_profile("steelwheels", profile_table(steelwheels_connection, "orders", columns=["STATUS"]))
    rows = graph.run("MATCH (:DataProfile {id:$id})-[:PROFILES]->(t:Table) RETURN t.name AS name", id=pid)
    assert [r["name"] for r in rows] == ["orders"]


@pytest.mark.req("AC-05")
def test_multi_column_observation_is_about_every_column(graph, repo, steelwheels_connection):
    pid = repo.save_profile(
        "steelwheels",
        profile_table(steelwheels_connection, "customers", columns=["CITY"], tuple_sets=[["CITY", "STATE", "COUNTRY"]]),
    )
    rows = graph.run(
        "MATCH (:DataProfile {id:$id})-[:HAS_SEGMENT]->(:ProfileSegment)-[:HAS_OBSERVATION]->(o:ProfileObservation)"
        "-[:ABOUT]->(c:Column) WITH o, collect(c.name) AS cols WHERE size(cols) = 3 RETURN cols",
        id=pid,
    )
    assert rows and set(rows[0]["cols"]) == {"CITY", "STATE", "COUNTRY"}
