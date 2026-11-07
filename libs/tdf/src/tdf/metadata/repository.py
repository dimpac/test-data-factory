"""Persist metadata, profiles and contracts to Neo4j using the ontology. Phase 1 stub."""

from __future__ import annotations

from typing import Any

from tdf.contracts.models import ContractSpec
from tdf.graph import GraphClient
from tdf.metadata.models import Relationship, SchemaModel
from tdf.profiling.profiler import ProfileResult


class MetadataRepository:
    def __init__(self, graph: GraphClient) -> None:
        self.graph = graph

    def register_database(
        self, name: str, schema: SchemaModel, physical: dict[str, dict[str, str]]
    ) -> None:
        """Create Database, Table and Column nodes and RELATES_TO edges. Idempotent."""
        raise NotImplementedError

    def get_schema(self, database: str) -> SchemaModel:
        raise NotImplementedError

    def get_relationships(self, database: str) -> list[Relationship]:
        raise NotImplementedError

    def save_profile(self, database: str, profile: ProfileResult) -> str:
        """Persist a DataProfile with its segment and observations; return the profile id."""
        raise NotImplementedError

    def list_profiles(self, database: str, table: str) -> list[dict[str, Any]]:
        raise NotImplementedError

    def get_profile(self, database: str, table: str, profile_id: str | None = None) -> ProfileResult:
        """Return the given profile, or the most recent one for the table."""
        raise NotImplementedError

    def save_contract(self, database: str, contract: ContractSpec) -> None:
        raise NotImplementedError

    def load_contract(self, database: str, table: str) -> ContractSpec:
        raise NotImplementedError
