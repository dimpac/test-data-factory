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
    children = {name: set() for name in schema.tables}
    indegree = {name: 0 for name in schema.tables}
    for relationship in schema.relationships:
        if relationship.parent == relationship.child:
            continue
        if relationship.child not in children[relationship.parent]:
            children[relationship.parent].add(relationship.child)
            indegree[relationship.child] += 1

    ready = sorted(name for name, degree in indegree.items() if degree == 0)
    ordered: list[str] = []
    while ready:
        table = ready.pop(0)
        ordered.append(table)
        for child in sorted(children[table]):
            indegree[child] -= 1
            if indegree[child] == 0:
                ready.append(child)
                ready.sort()
    if len(ordered) != len(schema.tables):
        cycle = sorted(name for name, degree in indegree.items() if degree)
        raise DependencyCycleError(f"Dependency cycle involving: {', '.join(cycle)}")
    return ordered
