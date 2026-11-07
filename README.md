# Test Data Factory

Test Data Factory (TDF) generates **synthetic, relationally consistent test data** for relational
databases from declared **contracts**, and then **independently validates** the generated data
against declared **expectations**. Metadata (schema, profiles, contracts, policies) lives in a
Neo4j graph; the sample source is the SteelWheels database in DuckDB; everything is driven from
one CLI, `tdf`.

**Demo in one block** (inside the devcontainer, from the repository root):

```bash
tdf metadata register --database steelwheels --erd docs/steelwheels_erd.mmd --source data/steelwheels.duckdb
tdf contract load libs/tdf/config/steelwheels/contract.yaml
for t in offices employees customers products orders orderdetails; do
  tdf profile --database steelwheels --source data/steelwheels.duckdb --table "$t"
done
tdf generate --database steelwheels --seed 42 --out out/steelwheels
tdf validate --database steelwheels --data-dir out/steelwheels   # exit 0 = no unexpected violations
```

Status: **Phase 1 (Foundational MVP)** of [`docs/PRD.md`](docs/PRD.md). See
[Known limitations](#9-known-limitations) before relying on anything not listed under
[Implemented capabilities](#3-implemented-capabilities).

## 1. Project overview

| Path | Purpose |
|---|---|
| `libs/tdf` | The TDF package and `tdf` CLI, with unit and integration tests |
| `libs/tdf/config/steelwheels/contract.yaml` | FUNCTIONAL generator contract for all six SteelWheels tables |
| `docs/PRD.md` | Requirements, acceptance criteria (AC-xx), roadmap, open architectural decisions (AD-xxx) |
| `docs/ONTOLOGY.md`, `docs/ontology.mmd` | Graph ontology (node labels, relationships) |
| `docs/steelwheels_erd.mmd` | SteelWheels ERD (Mermaid); the source of table relationships |
| `data/*.csv` | SteelWheels source tables, loaded into `data/steelwheels.duckdb` (generated, git-ignored) |
| `data/allCountriesCSV.csv.gz` | Postal-code reference (~1.4M rows) used by the `geo` generator |
| `.devcontainer/` | App + Neo4j containers, Compose, devcontainer config |
| `.instructions/`, `.plans/`, `.feedback/` | The prompts, plans and reviews used to build this with a coding agent |
| `apps/hello-world`, `libs/utils` | Scaffold starters; not part of TDF |

## 2. Problem being solved

Teams usually get test data by copying/masking production (privacy risk), hand-writing fixtures
(they rot), or calling random generators (structurally valid but semantically wrong: orders for
customers that do not exist, a city in the wrong country). TDF makes the test-data requirements
explicit — which tables, how many rows, which generators, which rules must hold — and then
**checks the output against those rules with a validator that does not share code with the
generators**, so "generation succeeded" is never mistaken for "the data is right".

## 3. Implemented capabilities

Everything below is exercised by the test suite.

- **Metadata registration** — parse a Mermaid ERD (including composite join columns), introspect
  DuckDB physical types, report missing tables/columns (errors) and type mismatches (warnings),
  persist Database/Table/Column/`RELATES_TO` to Neo4j idempotently.
- **Profiling** — per-column row/null/distinct counts, numeric min/max/mean/stddev, value sets and
  frequencies (capped at 100 distinct values, AD-005), multi-column value sets declared by the
  contract. Each run is stored as a distinct `DataProfile`.
- **Contracts and policies** — YAML contracts → Pydantic models → Neo4j. One policy per intent
  (`FUNCTIONAL`, `PERFORMANCE`, `EDGE`); generation uses `FUNCTIONAL`. Validation before any data
  is produced: unknown tables/columns/generators, column owned by two groups (AD-008), negative
  row counts.
- **Generation** — deterministic per seed (seed derived per table and column group); tables
  generated parent-first by topological order; cycles other than self-references rejected.
  Generators: `sequence`, `integer`, `float`, `string`, `boolean`, `date`, `timestamp`,
  `categorical` (fixed values or profile frequencies), `tuple` (profile value sets),
  `faker` (one provider per group), `geo` (real city/state/postcode/country rows, plus derived
  `TERRITORY`), `foreign_key`.
- **Relational integrity** — foreign keys reference generated parent rows only; nullable
  references via `null_ratio`; nullable self-references point at an earlier row (first row null,
  AD-006); multi-parent keys (e.g. `orderdetails(ORDERNUMBER, PRODUCTCODE)`) with optional
  uniqueness, sampled without materialising the Cartesian product.
- **Fail-loud generation** — a generator returning the wrong row count or columns raises
  `GenerationError` naming table, group, generator, expected and actual counts. Empty parents,
  missing parent specs and self-references to not-yet-generated keys raise `ContractError`.
- **Independent validation** — reads only the CSVs and expectations (enforced by a test).
  Types: `completeness`, `uniqueness`, `range`, `enumeration`, `volume`,
  `referential_integrity`, `tuple_in_set`. Outcomes: `SATISFIED`, `UNEXPECTED_VIOLATION`,
  `EXPECTED_VIOLATION` (`params.expect_violation: true`), `UNEVALUATED` (unsupported type or
  non-`APPROVED` status, with the reason). Misconfigured expectations (missing CSV, unknown column,
  missing parameter) are reported as `UNEXPECTED_VIOLATION` with `configuration error` evidence,
  never as passing. `tdf validate` exits non-zero on any unexpected violation.
- **CSV output** — nulls as empty fields, dates/timestamps as ISO 8601, schema column order.

## 4. Architecture and ontology

```
 ERD (.mmd) ─┐                         ┌─> Neo4j: Database/Table/Column/RELATES_TO
 DuckDB ─────┼─ tdf metadata register ─┤
             │                         │
 contract ───┼─ tdf contract load ─────┼─> GeneratorContract ─HAS_POLICY─> GenerationPolicy
 (.yaml)     │                         │       ├─HAS_COLUMN_GROUP─> ColumnGroup ─USES_GENERATOR─> Generator
             │                         │       └─ENFORCES─> Expectation
 DuckDB ─────┴─ tdf profile ───────────┴─> DataProfile ─HAS_SEGMENT─> ProfileSegment ─> ProfileObservation

 tdf generate:  load schema+contracts+profiles ─> validate contracts ─> order tables
                ─> per column group: generator ─> cardinality check ─> CSV per table
 tdf validate:  load APPROVED FUNCTIONAL expectations ─> read CSVs ─> outcome per expectation
```

Code map (`libs/tdf/src/tdf`): `metadata/` (ERD, introspection, schema check, Neo4j repository),
`profiling/`, `contracts/` (models, loader, pre-execution validation), `planning/` (dependency
order), `generators/` (registry), `engine.py` (orchestration and foreign keys), `output/`,
`validation/`, `cli.py`. The ontology is documented in [`docs/ONTOLOGY.md`](docs/ONTOLOGY.md);
Phase 1 provisional decisions (AD-001…AD-009) are in [`docs/PRD.md`](docs/PRD.md).

### Engineering decisions

| Decision | Rationale and trade-off |
|---|---|
| CLI, not web UI | Scriptable, testable with `CliRunner`, usable in CI and by coding agents. No visual exploration. |
| Neo4j as metadata control plane | Schema, relationships, profiles, contracts and expectations are a connected graph; queries like "which expectations touch this column" are traversals. Costs an extra service; generation itself does not run in the graph. |
| Contracts / policies / column groups / generators separated | A contract says *what* a table needs; a policy says *how* for one testing intent; column groups let correlated columns (city/state/country) be generated together; generators stay small and reusable. More configuration than a single script. |
| Profiling and expectations independent of generation | Profiles are evidence, expectations are approved requirements, and the validator never imports generators — so a generator bug cannot hide its own failure. |
| DuckDB + SteelWheels | Zero-server, embedded, fast SQL profiling over a small, well-known schema with a self-reference and a composite key. |
| Devcontainer for the coding agent | The agent runs as a non-root user in a container with only the repo mounted and read-only host OpenCode config; no Docker socket, no privileged mode. |
| Code Review Graph | Structural index (Tree-sitter) the agent queries over MCP for callers/impact instead of reading whole files. |
| Deterministic tests as acceptance | Tests are tagged with PRD requirement IDs (`@pytest.mark.req("AC-01")`); seeded generation makes output byte-reproducible, so tests compare hashes rather than eyeballing data. |

## 5. Quick start

For a production-style run of the `tdf` CLI with Neo4j, follow the step-by-step
[SteelWheels tutorial](TUTORIAL.md) (`docker compose build tdf`, then `docker compose run --rm tdf --help`).

The development container setup is described below.

Prerequisites: Docker (Compose v2) and VS Code with the Dev Containers extension (or plain
Compose). The images are built for `linux/amd64`.

```bash
cp .env.changeme .env          # then set a non-empty NEO4J_PASSWORD in .env (never commit it)
```

Open the folder in VS Code and choose **Reopen in Container**. On creation,
`.devcontainer/post-create.sh` installs `tdf` (editable), builds `data/steelwheels.duckdb` from
`data/*.csv`, and initialises Code Review Graph. The app container waits for Neo4j's health check.

Without VS Code:

```bash
docker compose -f .devcontainer/docker-compose.yml up -d --build
docker compose -f .devcontainer/docker-compose.yml exec test-data-factory-app .devcontainer/post-create.sh
docker compose -f .devcontainer/docker-compose.yml exec test-data-factory-app bash
```

Neo4j Browser: <http://localhost:7474>, Bolt: `bolt://localhost:7687` from the host,
`bolt://test-data-factory-graph:7687` from the app container. Neo4j `/data` is `tmpfs`: **all
graph metadata is lost when the container is recreated**, so re-run the registration steps.

## 6. End-to-end demonstration

From the repository root inside the app container (`NEO4J_*` comes from `.env` via Compose).

| Step | Command | Expected output |
|---|---|---|
| 1. Register schema | `tdf metadata register --database steelwheels --erd docs/steelwheels_erd.mmd --source data/steelwheels.duckdb` | `Registered steelwheels` |
| 2. Load contract and policies | `tdf contract load libs/tdf/config/steelwheels/contract.yaml` | `Loaded 6 contracts` |
| 3. Profile source (after step 2: the contract declares which value sets to profile) | `tdf profile --database steelwheels --source data/steelwheels.duckdb --table orders` (repeat per table, see top) | `Profiled orders: <id>` |
| 4. Generate (FUNCTIONAL policy) | `tdf generate --database steelwheels --seed 42 --out out/steelwheels` | `Generated 3597 rows in out/steelwheels` |
| 5. Validate | `tdf validate --database steelwheels --data-dir out/steelwheels` | 15 lines `…: SATISFIED`, exit code 0 |
| 6. Inspect | `head out/steelwheels/orders.csv` or `duckdb -c "select STATUS, count(*) from 'out/steelwheels/orders.csv' group by 1"` | |

Variations:

- Same seed ⇒ byte-identical CSVs; a different `--seed` changes them.
- `--rows orders=3000` overrides the policy's `row_count` for one run.
- Corrupt a foreign key (e.g. set one `CUSTOMERNUMBER` in `orders.csv` to `99999999`) and re-run
  step 5: `orders_customer_fk: UNEXPECTED_VIOLATION [('99999999',)]`, exit code 1.

Steps 1–5 take about 30 seconds; the first `geo` draw reads the 15 MB compressed postal file.
There is no separate run report yet (`tdf report` is a placeholder): the validate output and the
CSVs are the report.

## 7. Testing and verification

```bash
pytest libs/tdf/tests -m "not neo4j"   # unit tests; no services needed
pytest libs/tdf/tests                  # all tests; needs Neo4j and NEO4J_PASSWORD
```

Integration tests (`neo4j` marker) run the full CLI pipeline above against a dedicated
`tdf-test` Neo4j database, which the fixture creates and wipes. They are **skipped** if Neo4j is
unreachable or `NEO4J_PASSWORD` is unset, and `duckdb`-marked tests are skipped if
`data/steelwheels.duckdb` is missing — check the skip count. Outside Compose, export `.env` first
(`set -a; . ./.env; set +a`).

Coverage includes: generator determinism and parameters; generator output cardinality (exact,
insufficient, excessive, missing column); dependency ordering and cycle detection; foreign keys
for single, multi-parent, nullable, self-referencing and empty parents; contract validation;
every expectation type including misconfiguration; reproducible SteelWheels generation;
validation catching corruption after a successful generation; CLI smoke tests.

## 8. Agent-assisted engineering workflow

This repository was built with OpenCode in about three hours (commits `5d01b62`…`0ea92e5`), then
reviewed. The actual sequence, recorded in `.instructions/` (human prompts), `.plans/` (agent
plans and outcomes) and git history:

1. **Scaffold and isolate** — devcontainer, non-root user, read-only host agent config, Neo4j with
   ephemeral storage, `AGENTS.md` as the authoritative instructions (`CLAUDE.md` defers to it), a
   repository SKILL. One agent change (switching the base image to Node) was caught in review and
   reverted (`8933b21`).
2. **Requirements first** — ontology (`docs/ONTOLOGY.md`), then the PRD with acceptance criteria
   and open architectural decisions. `AGENTS.md` forbids resolving AD-xxx without approval; the
   Phase 1 choices are recorded as *provisional*.
3. **Tests before implementation** — a plan (`.plans/03_phase1_mvp.md`) agreeing the stack and
   provisional decisions, then stubs plus failing tests tagged with requirement IDs (`5266813`).
4. **Implementation to green** — `0ea92e5`, with the plan updated to record decisions, data
   quality findings and open items.
5. **Review with an approval gate** — `.feedback/04_phase1_mvp_implementation.md`: the agent
   inspected and probed the code, reported findings with file/line evidence and a plan, and
   **stopped until the human approved scope and decisions** before changing anything.
   Confirmed defects got regression tests that fail on the previous code.

Model selection and token use were not measured; no savings are claimed. Practices used to keep
context small: Code Review Graph for targeted structural lookups, deterministic tests and
throwaway probe scripts as evidence instead of agent judgement, and plans/instructions as files
so each session starts from written state rather than conversation history. Every commit was
reviewed and made by a human.

## 9. Known limitations

- **In-memory generation.** Every table is held as a list of dicts until written; the whole
  dataset is in memory at once. Fine for thousands to low millions of rows; no streaming or
  batching (PRD AC-10 is out of Phase 1 scope) and no upper bound on requested row counts.
- **Foreign keys.**
  - Composite foreign keys: only as one parent column per child column in multi-parent groups
    (`parents:`); a composite key into a *single* parent table is supported in the single-parent
    form (`parent_columns: [A, B]`), but not in `parents:` mode, and multi-parent groups cannot be
    nullable.
  - Cycles other than nullable self-references are rejected, not resolved (AD-006).
  - The first row of a self-referencing table is always null, even if the ERD says mandatory.
  - Contract foreign-key groups are not cross-checked against ERD relationships.
- **Negative testing.** An expectation marked `expect_violation` that is *not* violated reports
  `SATISFIED`, so a negative test that did not fire looks like a pass. How negative testing is
  represented is open decision AD-013.
- **Offline generation.** `tdf generate --contract … --erd …` does not load profiles, so contracts
  using profile-driven generators (`categorical` with `source: profile`, `tuple`) — including the
  SteelWheels contract — only generate via the Neo4j path.
- **Contract drift.** The graph copy of a contract is not checked against the YAML; re-run
  `tdf contract load` after edits.
- **Generator realism.** Employee `EXTENSION`/`JOBTITLE` and product names are random strings;
  emails are not derived from names; prices are integers; order dates are not ordered
  (`SHIPPEDDATE` may precede `ORDERDATE`) because no cross-column rule exists yet.
- **Reference data.** `TERRITORY` for countries absent from the source offices is an assumed
  grouping; the postal file contains some double-encoded names (e.g. `Bacău`).
- **Not implemented** (ontology may represent them, the code does not): `tdf report`, `tdf repair`,
  generation run/plan records, PERFORMANCE/EDGE generation, expectation inference from profiles,
  statistical synthesis, adaptive learning.
- **Containers.** Neo4j image tag is floating (`neo4j:5-enterprise`); ports are published on all
  interfaces; the `production` image contains only hello-world, not `tdf`.

## 10. Future roadmap

From [`docs/PRD.md`](docs/PRD.md): **P2** advanced generation (cross-column rules, richer
generators, negative/edge policies), **P3** performance engineering (streaming/batched generation,
bounded memory, measured throughput; possibly Rust/Polars per AD-010/AD-012), **P4** adaptive
quality (repair, learning from failures), **P5** extended test-data management.

## Appendix: development environment

- The app image (`.devcontainer/Dockerfile.app`) has `runtime`, `development` and `production`
  targets; development adds OpenCode `1.19.3` (keep aligned with the host), Code Review Graph
  `2.3.9`, the DuckDB CLI and pinned Python dependencies from `requirements.txt`. Locale
  `en_AU.UTF-8`, timezone `Australia/Sydney`.
- Rebuild the SteelWheels database after changing `data/*.csv`:
  `python .devcontainer/setup-steelwheels.py` (only uncompressed `*.csv` files are imported).
- Code Review Graph runs as an MCP server launched by OpenCode (`opencode.json`); check with
  `opencode mcp list` and `code-review-graph status`.
