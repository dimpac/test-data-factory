"""Neo4j access. Phase 1 stub."""

from __future__ import annotations

from typing import Any


class GraphClient:
    """Thin wrapper over the Neo4j driver bound to one database."""

    @classmethod
    def from_env(cls, database: str | None = None) -> "GraphClient":
        """Build a client from NEO4J_URL, NEO4J_USERNAME, NEO4J_PASSWORD and NEO4J_DATABASE."""
        raise NotImplementedError

    def run(self, query: str, **parameters: Any) -> list[dict[str, Any]]:
        """Run a Cypher query and return rows as dictionaries."""
        raise NotImplementedError

    def close(self) -> None:
        raise NotImplementedError
