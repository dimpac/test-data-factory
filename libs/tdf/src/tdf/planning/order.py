"""Table dependency ordering. Phase 1 stub."""

from __future__ import annotations

from tdf.metadata.models import SchemaModel


class DependencyCycleError(ValueError):
    """The tables have a dependency cycle that cannot be ordered."""


def generation_order(schema: SchemaModel) -> list[str]:
    """Return tables with parents before children.

    Self-references are allowed (provisional AD-006). Any other cycle raises
    DependencyCycleError naming the tables involved.
    """
    raise NotImplementedError
