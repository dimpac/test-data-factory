# Decisions

## D1. CLI first, no web UI
- **Alternatives:** web UI; library only.
- **Why:** scriptable, testable with `CliRunner`, usable from CI and by coding agents.
- **Consequences:** no visual exploration; metadata is inspected with Cypher (see TUTORIAL step 13).

## D2. Neo4j as the metadata control plane
- **Alternatives:** YAML files only; a relational metadata schema.
- **Why:** schema, relationships, profiles, contracts and expectations form a connected graph;
  questions such as "which expectations touch this column" are traversals.
- **Consequences:** an extra service (Neo4j Enterprise licence terms apply), ephemeral data in dev,
  and drift between YAML and the stored copy until `contract load` is re-run. Generation itself
  does not run in the graph.

## D3. Contracts, policies, column groups and generators are separate
- **Alternatives:** one script or config per table.
- **Why:** a contract says what a table needs; a policy says how for one testing intent; column groups
  generate correlated columns together (city/state/country); generators stay small.
- **Consequences:** more configuration. Column ownership overlaps are rejected (AD-008, provisional).

## D4. Requirements first, tests before implementation, human approval gates
- **Alternatives:** prompt-and-iterate on code.
- **Why:** the PRD and acceptance criteria were written first; failing tests tagged with requirement
  IDs preceded the implementation (`5266813` then `0ea92e5`); review findings were approved by a
  human before changes (`.feedback/`).
- **Consequences:** slower first hour; objective acceptance. Details in
  [`agentic-workflow.md`](agentic-workflow.md).

## D5. Deliberate limits of the three-hour MVP
- **Accepted:** in-memory generation, FUNCTIONAL intent only, Python generators (no Rust or
  statistical synthesis), no `report`/`repair`, simple foreign-key shapes.
- **Why:** one verifiable workflow is worth more than breadth.
- **Consequences:** listed in the README "Known limitations".
