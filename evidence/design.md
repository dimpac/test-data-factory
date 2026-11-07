# Design

## Architecture as implemented
One CLI (`tdf`, Click) over a Python package in `libs/tdf/src/tdf`. Neo4j is the metadata store;
DuckDB is the read-only data source; CSV is the output.

```
ERD (.mmd) + DuckDB --metadata register--> Neo4j: Database/Table/Column/RELATES_TO
contract.yaml ------contract load--------> GeneratorContract > GenerationPolicy > ColumnGroup > Generator, Expectation
DuckDB -------------profile-------------> DataProfile > ProfileSegment > ProfileObservation
generate: load schema, contracts, profiles -> validate contracts -> order tables (parents first)
          -> per column group: generator -> cardinality check -> CSV per table
validate: load APPROVED FUNCTIONAL expectations -> read CSVs only -> outcome per expectation
```

Code map: `metadata/` (ERD, introspection, repository), `profiling/`, `contracts/`, `planning/`
(dependency order), `generators/`, `engine.py`, `output/`, `validation/`, `cli.py`.

## Ontology and diagrams
Graph ontology: [`docs/ONTOLOGY.md`](../docs/ONTOLOGY.md), source [`docs/ontology.mmd`](../docs/ontology.mmd).
SteelWheels ERD: [`docs/steelwheels_erd.mmd`](../docs/steelwheels_erd.mmd). Only the node labels the
CLI writes are used by the tutorial queries; others (for example `GenerationRun`) are defined for
later phases.

## Key trade-offs
See [`decisions.md`](decisions.md). In short: CLI over UI, Neo4j as control plane, contracts separate
from policies, in-memory generation for simplicity.

## Security
- Credentials come from `.env` / environment only; nothing is baked into images (checked: the image
  environment has no `NEO4J_*` values).
- The production image runs as non-root `tdf` (uid 1000), has no pytest, git or agent tooling, no
  privileged mode and no Docker socket. Bundled example assets are root-owned and read-only.
- Neo4j ports are published on `127.0.0.1` only in `compose.yaml`. The devcontainer Neo4j publishes
  on all interfaces (known limitation).
- The validator reads only CSVs and expectations and shares no code with generators (enforced by a test).

## Future production shape (not built)
Streaming/batched generation, a run/report record in the graph, a managed Neo4j (or Aurora-style
alternative per AD decisions), image published to a registry, and the generation job run as a
containerised batch task. See [`operate.md`](operate.md) for the CI/CD path.
