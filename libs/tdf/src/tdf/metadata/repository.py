"""Persist metadata, profiles and contracts to Neo4j using the ontology. Phase 1 stub."""

from __future__ import annotations

import json
from typing import Any

from tdf.contracts.models import ContractSpec
from tdf.graph import GraphClient
from tdf.metadata.models import Column, Relationship, SchemaModel, Table
from tdf.profiling.profiler import Observation, ProfileResult


class MetadataRepository:
    def __init__(self, graph: GraphClient) -> None:
        self.graph = graph

    def register_database(
        self, name: str, schema: SchemaModel, physical: dict[str, dict[str, str]]
    ) -> None:
        """Create Database, Table and Column nodes and RELATES_TO edges. Idempotent."""
        self.graph.run("MERGE (:Database {name:$database})", database=name)
        for table_index, (table_name, table) in enumerate(schema.tables.items()):
            self.graph.run(
                "MATCH (d:Database {name:$database}) "
                "MERGE (t:Table {database:$database, name:$table}) "
                "SET t.position=$position MERGE (d)-[:HAS_TABLE]->(t)",
                database=name, table=table_name, position=table_index,
            )
            for column_index, column in enumerate(table.columns):
                physical_type = physical.get(table_name, {}).get(column.name)
                self.graph.run(
                    "MATCH (t:Table {database:$database, name:$table}) "
                    "MERGE (c:Column {database:$database, table:$table, name:$column}) "
                    "SET c.type=$type, c.physical_type=$physical_type, c.primary_key=$primary_key, "
                    "c.foreign_key=$foreign_key, c.position=$position "
                    "MERGE (t)-[:HAS_COLUMN]->(c)",
                    database=name, table=table_name, column=column.name, type=column.type,
                    physical_type=physical_type, primary_key=column.primary_key,
                    foreign_key=column.foreign_key, position=column_index,
                )
        for relationship in schema.relationships:
            relationship_id = (
                f"{name}:{relationship.parent}:{relationship.child}:"
                f"{','.join(relationship.child_columns)}"
            )
            self.graph.run(
                "MATCH (p:Table {database:$database, name:$parent}), "
                "(c:Table {database:$database, name:$child}) "
                "MERGE (p)-[r:RELATES_TO {id:$id}]->(c) "
                "SET r.parent_columns=$parent_columns, r.child_columns=$child_columns, "
                "r.cardinality=$cardinality, r.optional=$optional",
                database=name, parent=relationship.parent, child=relationship.child,
                id=relationship_id, parent_columns=relationship.parent_columns,
                child_columns=relationship.child_columns, cardinality=relationship.cardinality,
                optional=relationship.optional,
            )

    def get_schema(self, database: str) -> SchemaModel:
        rows = self.graph.run(
            "MATCH (:Database {name:$database})-[:HAS_TABLE]->(t:Table)-[:HAS_COLUMN]->(c:Column) "
            "RETURN t.name AS table, t.position AS table_position, c.name AS name, c.type AS type, "
            "c.primary_key AS primary_key, c.foreign_key AS foreign_key, c.position AS position "
            "ORDER BY table_position, position",
            database=database,
        )
        tables: dict[str, Table] = {}
        for row in rows:
            tables.setdefault(row["table"], Table(name=row["table"], columns=[])).columns.append(
                Column(name=row["name"], type=row["type"],
                       primary_key=row["primary_key"], foreign_key=row["foreign_key"])
            )
        return SchemaModel(tables=tables, relationships=self.get_relationships(database))

    def get_relationships(self, database: str) -> list[Relationship]:
        rows = self.graph.run(
            "MATCH (p:Table {database:$database})-[r:RELATES_TO]->(c:Table {database:$database}) "
            "RETURN p.name AS parent, c.name AS child, r.parent_columns AS parent_columns, "
            "r.child_columns AS child_columns, r.cardinality AS cardinality, r.optional AS optional "
            "ORDER BY r.id",
            database=database,
        )
        return [Relationship.model_validate(row) for row in rows]

    def save_profile(self, database: str, profile: ProfileResult) -> str:
        """Persist a DataProfile with its segment and observations; return the profile id."""
        created_at = profile.created_at.isoformat()
        self.graph.run(
            "MATCH (t:Table {database:$database, name:$table}) "
            "MERGE (p:DataProfile {id:$id}) "
            "SET p.table=$table, p.database=$database, p.created_at=$created_at, p.config_json=$config "
            "MERGE (p)-[:PROFILES]->(t) "
            "MERGE (s:ProfileSegment {id:$segment_id}) SET s.name='ALL' "
            "MERGE (p)-[:HAS_SEGMENT]->(s)",
            database=database, table=profile.table, id=profile.id, created_at=created_at,
            config=json.dumps(profile.config, default=str), segment_id=f"{profile.id}:ALL",
        )
        for index, observation in enumerate(profile.observations):
            observation_id = f"{profile.id}:{index}"
            self.graph.run(
                "MATCH (s:ProfileSegment {id:$segment_id}) "
                "MERGE (o:ProfileObservation {id:$observation_id}) "
                "SET o.value_json=$value, o.columns=$columns, o.position=$position "
                "MERGE (s)-[:HAS_OBSERVATION]->(o) "
                "MERGE (m:ProfileMetric {name:$metric}) MERGE (o)-[:USES_METRIC]->(m)",
                segment_id=f"{profile.id}:ALL", observation_id=observation_id,
                value=json.dumps(observation.value, default=str), columns=observation.columns,
                position=index, metric=observation.metric,
            )
            for column in observation.columns:
                self.graph.run(
                    "MATCH (o:ProfileObservation {id:$observation_id}), "
                    "(c:Column {database:$database, table:$table, name:$column}) "
                    "MERGE (o)-[:ABOUT]->(c)",
                    observation_id=observation_id, database=database,
                    table=profile.table, column=column,
                )
        return profile.id

    def list_profiles(self, database: str, table: str) -> list[dict[str, Any]]:
        return self.graph.run(
            "MATCH (p:DataProfile {database:$database, table:$table})-[:HAS_SEGMENT]->(s:ProfileSegment) "
            "RETURN p.id AS id, p.created_at AS created_at, s.name AS segment "
            "ORDER BY p.created_at",
            database=database, table=table,
        )

    def get_profile(self, database: str, table: str, profile_id: str | None = None) -> ProfileResult:
        """Return the given profile, or the most recent one for the table."""
        if profile_id is None:
            matches = self.graph.run(
                "MATCH (p:DataProfile {database:$database, table:$table}) "
                "RETURN p.id AS id ORDER BY p.created_at DESC LIMIT 1",
                database=database, table=table,
            )
            if not matches:
                raise KeyError(f"No profile for {database}.{table}")
            profile_id = matches[0]["id"]
        profile_rows = self.graph.run(
            "MATCH (p:DataProfile {id:$id}) RETURN p.id AS id, p.table AS table, "
            "p.created_at AS created_at, p.config_json AS config",
            id=profile_id,
        )
        if not profile_rows:
            raise KeyError(f"Unknown profile {profile_id}")
        observations = self.graph.run(
            "MATCH (:DataProfile {id:$id})-[:HAS_SEGMENT]->(s:ProfileSegment)"
            "-[:HAS_OBSERVATION]->(o:ProfileObservation)-[:USES_METRIC]->(m:ProfileMetric) "
            "RETURN m.name AS metric, o.columns AS columns, o.value_json AS value, "
            "s.name AS segment ORDER BY o.position",
            id=profile_id,
        )
        row = profile_rows[0]
        return ProfileResult(
            id=row["id"], table=row["table"], created_at=row["created_at"],
            config=json.loads(row["config"] or "{}"),
            observations=[
                Observation(metric=item["metric"], columns=item["columns"],
                            value=json.loads(item["value"]), segment=item["segment"])
                for item in observations
            ],
        )

    def save_contract(self, database: str, contract: ContractSpec) -> None:
        contract_id = f"{database}:{contract.table}:{contract.version}"
        self.graph.run(
            "MATCH (t:Table {database:$database, name:$table}) "
            "MERGE (c:GeneratorContract {id:$id}) "
            "SET c.name=$name, c.version=$version, c.data_json=$data "
            "MERGE (t)-[:HAS_GENERATOR_CONTRACT]->(c)",
            database=database, table=contract.table, id=contract_id, name=contract.name,
            version=contract.version, data=contract.model_dump_json(),
        )
        for policy in contract.policies:
            policy_id = f"{contract_id}:{policy.name}"
            self.graph.run(
                "MATCH (c:GeneratorContract {id:$contract_id}) "
                "MERGE (p:GenerationPolicy {id:$id}) "
                "SET p.name=$name, p.intent=$intent, p.row_count=$row_count "
                "MERGE (c)-[:HAS_POLICY]->(p)",
                contract_id=contract_id, id=policy_id, name=policy.name,
                intent=policy.intent, row_count=policy.row_count,
            )
            # Remove groups from an earlier load of this policy so the graph matches the file.
            self.graph.run(
                "MATCH (:GenerationPolicy {id:$policy_id})-[:HAS_COLUMN_GROUP]->(g:ColumnGroup) "
                "WHERE NOT g.id IN $keep DETACH DELETE g",
                policy_id=policy_id,
                keep=[f"{policy_id}:{group.name}" for group in policy.column_groups],
            )
            for position, group in enumerate(policy.column_groups):
                group_id = f"{policy_id}:{group.name}"
                self.graph.run(
                    "MATCH (p:GenerationPolicy {id:$policy_id}) "
                    "MERGE (g:ColumnGroup {id:$id}) "
                    "SET g.name=$name, g.params_json=$params, g.position=$position "
                    "MERGE (p)-[:HAS_COLUMN_GROUP]->(g) "
                    "MERGE (gen:Generator {name:$generator}) MERGE (g)-[:USES_GENERATOR]->(gen)",
                    policy_id=policy_id, id=group_id, name=group.name,
                    params=json.dumps(group.params), position=position, generator=group.generator,
                )
                for column in group.columns:
                    self.graph.run(
                        "MATCH (g:ColumnGroup {id:$group_id}), "
                        "(c:Column {database:$database, table:$table, name:$column}) "
                        "MERGE (g)-[:INCLUDES]->(c)",
                        group_id=group_id, database=database, table=contract.table, column=column,
                    )
            for expectation in policy.expectations:
                expectation_id = f"{policy_id}:{expectation.id}"
                self.graph.run(
                    "MATCH (p:GenerationPolicy {id:$policy_id}) "
                    "MERGE (e:Expectation {node_id:$node_id}) "
                    "SET e.id=$id, e.type=$type, e.scope=$scope, e.source=$source, "
                    "e.status=$status, e.params_json=$params "
                    "MERGE (p)-[:ENFORCES]->(e)",
                    policy_id=policy_id, node_id=expectation_id, id=expectation.id,
                    type=expectation.type, scope=expectation.scope, source=expectation.source,
                    status=expectation.status, params=json.dumps(expectation.params),
                )

    def load_contract(self, database: str, table: str) -> ContractSpec:
        rows = self.graph.run(
            "MATCH (:Table {database:$database, name:$table})-[:HAS_GENERATOR_CONTRACT]->"
            "(c:GeneratorContract) RETURN c.data_json AS data ORDER BY c.version DESC LIMIT 1",
            database=database, table=table,
        )
        if not rows:
            raise KeyError(f"No contract for {database}.{table}")
        return ContractSpec.model_validate_json(rows[0]["data"])
