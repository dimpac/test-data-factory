# Intent

## Problem
Test data usually comes from masked production copies (privacy risk), hand-written fixtures (they
rot) or random generators (structurally valid, semantically wrong). Test Data Factory (TDF) makes
test-data requirements explicit as contracts, generates synthetic relational data from them, and
validates the result with an independent validator. Full requirements: [`docs/PRD.md`](../docs/PRD.md).

## Users
Engineers and test engineers who need relationally consistent test data for a relational database,
and coding agents that drive the same CLI.

## Assumptions
- The source schema is described by a Mermaid ERD plus a DuckDB file (SteelWheels sample).
- A local Docker engine is available; Neo4j Enterprise is accepted for evaluation use.
- Data volumes are small enough to hold in memory (thousands to low millions of rows).

## Constraints
- Three-hour MVP timebox (Phase 1 of the PRD), then a review and packaging pass.
- Local only: no paid services, no private repositories.
- Open architectural decisions (AD-xxx) are provisional and are not resolved without approval.

## Exclusions
Web UI, statistical or ML synthesis (CTGAN), Rust, autonomous repair, streaming generation,
PERFORMANCE/EDGE generation, report records. See the README "Known limitations".

## Success criteria
One workflow works end to end with the real CLI: register SteelWheels metadata, load the contract,
profile, generate CSV, validate (15 expectations satisfied), reject a corrupted dataset. It is
reproducible from a clean checkout with Docker (`scripts/verify.sh --integration`).
