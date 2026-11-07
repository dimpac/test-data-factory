"""Neo4j access. Phase 1 stub."""

from __future__ import annotations

import os
from typing import Any

from neo4j import GraphDatabase


class GraphClient:
    """Thin wrapper over the Neo4j driver bound to one database."""

    def __init__(self, driver: Any, database: str) -> None:
        self.driver = driver
        self.database = database

    @classmethod
    def from_env(cls, database: str | None = None) -> "GraphClient":
        """Build a client from NEO4J_URL, NEO4J_USERNAME, NEO4J_PASSWORD and NEO4J_DATABASE."""
        url = os.environ.get("NEO4J_URL", "bolt://test-data-factory-graph:7687")
        username = os.environ.get("NEO4J_USERNAME", "neo4j")
        password = os.environ.get("NEO4J_PASSWORD")
        if not password:
            raise ValueError("NEO4J_PASSWORD is required")
        selected_database = database or os.environ.get("NEO4J_DATABASE", "neo4j")
        return cls(GraphDatabase.driver(url, auth=(username, password)), selected_database)

    def run(self, query: str, **parameters: Any) -> list[dict[str, Any]]:
        """Run a Cypher query and return rows as dictionaries."""
        records, _, _ = self.driver.execute_query(
            query, parameters_=parameters, database_=self.database
        )
        return [dict(record) for record in records]

    def close(self) -> None:
        self.driver.close()
