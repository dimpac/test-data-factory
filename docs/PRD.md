# Test Data Factory - Product Requirements Document

| | |
|--|--|
| Status | Draft |
| Date | 2026-11-07 |
| Related | [`ONTOLOGY.md`](ONTOLOGY.md), [`ontology.mmd`](ontology.mmd) |

## Summary

Test Data Factory (TDF) is a unified tool for generating synthetic test data for relational databases. It combines profiling, contract-driven generation, validation and repair in one workflow, using a graph-based metadata control plane.

## Problem

Engineering teams frequently struggle to obtain suitable test data.

Common approaches include:

1. Manually creating small sets of test records.
2. Copying or masking production data.
3. Generating random values using libraries such as Faker.
4. Using statistical models to create synthetic datasets.
5. Maintaining bespoke scripts for individual testing scenarios.

These approaches have limitations:

- Random generators may produce structurally valid but semantically inconsistent records.
- Production-derived datasets may introduce privacy, security and operational risks.
- Statistical generators may reproduce distributions without preserving important business rules.
- Manually maintained test fixtures can become difficult to maintain as application schemas evolve.
- Performance testing often requires specially constructed data distributions that do not naturally occur in production samples.
- Existing solutions frequently separate data profiling, generation, validation and repair into disconnected workflows.

TDF aims to provide a unified approach.

## Objectives

- Generate datasets according to explicit testing objectives, rather than relying on a single universal generation strategy.
- Define measurable expectations that generated datasets must satisfy or intentionally violate.
- Use database schemas, relational dependencies, profiling observations and generation policies to construct execution plans.
- Support deterministic data generation where the chosen algorithm permits it.
- Generate data across related tables while preserving declared structural constraints, except where violations are explicitly requested.
- Support large-scale generation with bounded resource consumption and measurable performance.
- Allow new generators, profiling metrics, expectations, validators and repair strategies to be introduced without redesigning the core system.
- Explain which generation strategies were selected, which expectations were evaluated and why generated datasets passed or failed validation.
- Provide a foundation for learning from generation failures and improving subsequent generation plans.

## Concepts

Ontology labels are defined in [`ONTOLOGY.md`](ONTOLOGY.md).

### Data Profile

Ontology: `DataProfile`.

A Data Profile represents observed characteristics of an existing dataset. Profiles provide evidence about source-data structure, quality and statistical behaviour. Profiling results are observations, not automatically approved requirements.

### Expectation

Ontology: `Expectation`.

An Expectation defines an assertion about a dataset. Expectations may describe:

- Structural requirements.
- Completeness.
- Uniqueness.
- Valid ranges and enumerations.
- Referential integrity.
- Statistical distributions.
- Business rules.
- Expected negative-test violations.

Expectations may be inferred, imported or explicitly declared.

### Generator Contract

Ontology: `GeneratorContract`.

A Generator Contract defines the requirements governing synthetic-data generation for a table or other supported generation scope. Contracts establish the intended testing outcomes and applicable policies.

### Generation Policy

Ontology: `GenerationPolicy`.

A Generation Policy defines how a contract is fulfilled for a particular generation intent. Policies coordinate column groups, generator selection and applicable expectations.

### Column Group

Ontology: `ColumnGroup`.

A Column Group identifies columns that must be generated together. Column grouping supports correlated attributes, consistent business concepts and coordinated generation.

### Generator

Ontology: `Generator`.

A Generator is an executable capability responsible for producing synthetic values. Generators are reusable and should remain independent of particular datasets where practical.

### Generation Plan

Ontology: `GenerationPlan`.

A Generation Plan is the resolved set of execution instructions derived from contracts, policies, column groups, metadata and available profiling observations. It identifies the selected generators, dependencies, parameters and validation requirements.

### Generation Run

Ontology: `GenerationRun`.

A Generation Run represents one execution of a generation plan, including its configuration, seed, outputs, validation results and execution metadata.

## Functional Requirements

### Database Metadata Management

- **FR-META-01:** The system should support registration of a database and its associated tables.
- **FR-META-02:** The system should represent tables and their associated columns.
- **FR-META-03:** The system should capture column names, logical data types, nullability and other relevant structural characteristics.
- **FR-META-04:** The system should represent relationships between tables, including:
    - Relationship direction.
    - Cardinality.
    - Parent and child keys.
    - Composite keys.
    - Optionality where known.
- **FR-META-05:** The system should detect invalid or unresolved metadata references.
- **FR-META-06:** The system should support querying table dependencies to assist generation planning and ordering.

### Data Profiling

- **FR-PROF-01:** The system should profile supported source datasets and produce a Data Profile.
- **FR-PROF-02:** The initial profiling capability should support applicable metrics including:
    - Row count.
    - Null count.
    - Non-null count.
    - Distinct non-null count.
    - Minimum value.
    - Maximum value.
    - Mean.
    - Standard deviation.
    - Value set for bounded-cardinality columns.
    - Value frequencies.
- **FR-PROF-03:** Each profiling observation should identify the metric used, measured value, applicable column and profile segment.
- **FR-PROF-04:** The system should support profiling an entire table and, in a later increment, selected subsets of records.
- **FR-PROF-05:** Profiles should preserve enough metadata to identify their source, profiling configuration and execution time.
- **FR-PROF-06:** The system should support multiple profiles for the same table without silently overwriting previous observations.
- **FR-PROF-07:** Large categorical distributions, histograms and other complex profiling outputs may be stored in external artefacts referenced by the metadata graph.

### Expectation Management

- **FR-EXP-01:** The system should maintain a catalogue of supported expectation types. Initial expectation families should include:
    - Schema and type.
    - Completeness.
    - Uniqueness.
    - Range and enumeration.
    - Statistical.
    - Volume.
    - Relational integrity.
- **FR-EXP-02:** Each expectation should define its type, target scope and relevant validation parameters.
- **FR-EXP-03:** The system should distinguish inferred, explicitly declared and imported expectations.
- **FR-EXP-04:** The system should support proposed and approved expectations, with rejection or retirement where applicable.
- **FR-EXP-05:** The system should support deriving candidate expectations from profiling observations.
- **FR-EXP-06:** Inferred expectations should not automatically become authoritative business constraints.
- **FR-EXP-07:** The system should support test scenarios requiring selected expectations to be deliberately violated.
- **FR-EXP-08:** Expectation evaluation should produce a measurable result, including relevant failures and diagnostics.

### Generator Contracts and Policies

- **FR-CON-01:** The system should support defining and retrieving generator contracts associated with tables.
- **FR-CON-02:** The system should initially recognise the intents `FUNCTIONAL`, `PERFORMANCE` and `EDGE`.
- **FR-CON-03:** The design should permit additional intents, including explicit negative and statistical-fidelity testing (see AD-013).
- **FR-CON-04:** A generator contract should support one or more generation policies.
- **FR-CON-05:** Generation policies should define column groups representing coordinated units of generation.
- **FR-CON-06:** Each column group should identify the columns under its responsibility.
- **FR-CON-07:** Column groups should select compatible generators based on their configured policies.
- **FR-CON-08:** The model should support generator parameters and, when required, generator priority or fallback selection.
- **FR-CON-09:** The system should detect conflicting generator ownership of the same column within a resolved execution plan.
- **FR-CON-10:** The system should validate a generator contract before execution, detecting missing references, unsupported generators and inconsistent rules.

### Synthetic Data Generation

- **FR-GEN-01:** The system should support seeded deterministic generators for reproducible datasets.
- **FR-GEN-02:** The initial generators should support common relational types, including integers, floating-point numbers, strings, booleans, dates and timestamps.
- **FR-GEN-03:** Generators should be able to use applicable profiling observations when determining generation parameters.
- **FR-GEN-04:** The system should support configurable null frequencies, subject to applicable constraints.
- **FR-GEN-05:** The system should support categorical generation using declared sets or observed frequency distributions.
- **FR-GEN-06:** The system should support numeric generation within configured ranges and selected distributions.
- **FR-GEN-07:** A generator should be able to produce multiple related column values together.
- **FR-GEN-08:** The system should support generating related tables while preserving required foreign-key relationships.
- **FR-GEN-09:** The system should derive a valid execution sequence from known dependencies where possible, and report unsupported cyclic dependencies.
- **FR-GEN-10:** The system should support specifying required record counts.
- **FR-GEN-11:** The system should support configurable data skew and cardinality for performance-testing scenarios.
- **FR-GEN-12:** The system should support generating deliberate boundary cases and controlled invalid records.
- **FR-GEN-13:** The initial release should support CSV output. Parquet and database writers are subsequent priorities.
- **FR-GEN-14:** Large data generation should support incremental output without requiring the complete dataset to reside in memory.

### Validation and Repair

- **FR-VAL-01:** The system should validate generated datasets against the expectations applicable to the selected generation policy.
- **FR-VAL-02:** Validation results should distinguish:
    - Satisfied expectations.
    - Unexpected violations.
    - Expected violations.
    - Unsupported or unevaluated expectations.
- **FR-VAL-03:** Generators should not determine their own validation success.
- **FR-VAL-04:** Validation failures should identify the affected expectation, dataset scope and relevant evidence.
- **FR-VAL-05:** A future capability should classify generation failures and identify candidate repair strategies.
- **FR-VAL-06:** Repair operations should be bounded by the contract and should not silently modify approved expectations.
- **FR-VAL-07:** Repaired datasets should be revalidated, including checks for regressions introduced by repair operations.
- **FR-VAL-08:** The system should preserve records of repair attempts, outcomes and unresolved violations.
- **FR-VAL-09:** A future capability should use repeated failure patterns to propose improvements to generation strategies.
- **FR-VAL-10:** Automatically proposed strategy improvements should be tested before being promoted to approved reusable behaviour.

### CLI

- **FR-CLI-01:** All essential capabilities should be accessible through a command-line interface.
- **FR-CLI-02:** The system should provide commands equivalent to:
    - `tdf metadata`
    - `tdf profile`
    - `tdf contract`
    - `tdf generate`
    - `tdf validate`
    - `tdf repair`
    - `tdf report`

## Non-Functional Requirements

### Performance

- **NFR-PERF-01:** The generation engine should support streaming or batch-based processing with bounded memory consumption.
- **NFR-PERF-02:** Generation throughput should be measurable in records per second.
- **NFR-PERF-03:** Peak memory utilisation and generation duration should be recorded for performance benchmarks.
- **NFR-PERF-04:** The architecture should permit optimised generation components written in Rust.
- **NFR-PERF-05:** A future benchmark should evaluate generation of 10 million relationally consistent records on a developer workstation.
- **NFR-PERF-06:** A longer-term performance target should evaluate 100 million records under documented resource constraints.

These volume targets are engineering objectives, not established performance guarantees.

### Reliability and Reproducibility

- **NFR-REL-01:** Identical supported configurations, seeds and execution versions should produce reproducible results.
- **NFR-REL-02:** Failures should provide actionable diagnostics.
- **NFR-REL-03:** Partial output should not be reported as a successful completed dataset.
- **NFR-REL-04:** Execution reports should identify the contract, policy, generator versions and configuration used.

### Security

- **NFR-SEC-01:** The default development environment should use containers.
- **NFR-SEC-02:** Coding agents should operate within a restricted development environment.
- **NFR-SEC-03:** Container permissions, filesystem mounts and network access should follow least-privilege principles.
- **NFR-SEC-04:** No production credentials or confidential datasets should be committed to the repository.
- **NFR-SEC-05:** Source profiling should avoid unnecessary retention of raw source values.
- **NFR-SEC-06:** Statistical similarity alone should not be considered sufficient evidence of privacy protection.

### Maintainability

- **NFR-MAINT-01:** The system should use clearly separated responsibilities for metadata, profiling, planning, generation, validation and reporting.
- **NFR-MAINT-02:** Core components should expose documented contracts or interfaces.
- **NFR-MAINT-03:** Generator implementations should be independently testable.
- **NFR-MAINT-04:** The system should support local development without paid cloud services.

### Usability

- **NFR-USE-01:** Core workflows should be executable through documented CLI commands.
- **NFR-USE-02:** Error messages should identify the failure and, where practical, a corrective action.
- **NFR-USE-03:** The repository should include runnable sample configurations and datasets.
- **NFR-USE-04:** The initial release should not require a web UI.

## Proposed Technology Direction

The following technologies are proposed architectural choices, not requirements for every future deployment.

| Component | Proposed technology | Rationale |
|--|--|--|
| Orchestration and CLI | Python | Familiar ecosystem and rapid development |
| Metadata control plane | Neo4j | Visual graph modelling, Cypher and traversal |
| Graph extensions | APOC | Supporting graph operations where justified |
| Source and sample database | DuckDB | Embedded and file-based with no server; already in the development image; hosts the SteelWheels sample (`data/steelwheels.duckdb`) |
| Data profiling | Python / pandas (via DuckDB) | Phase 1 uses DuckDB and pandas. Polars is deferred |
| Initial generators | Python | Rapid development and verification |
| Optimised generation engine | Rust | Efficient high-volume generation |
| Data interchange | Apache Arrow | Columnar interoperability |
| Output storage | CSV, Parquet, database writers | Portable test data |
| Local runtime | Docker Compose | Reproducible local services |
| Development isolation | Devcontainers | Controlled environment for tools and agents |
| Testing | Pytest and appropriate integration tools | Deterministic verification |

No particular technology should be retained solely because it was selected during prototyping. Performance and maintainability evidence should guide later architectural decisions.

## Acceptance Criteria and Example Scenarios

**AC-01**
Given a source schema containing Customers and Orders, with Orders referencing Customers,
when a functional generation policy produces synthetic data,
then every generated order should reference a valid generated customer, unless an intentional violation is specified.

**AC-02**
Given a supported deterministic generator, fixed contract, seed and execution version,
when generation executes twice,
then both outputs should contain equivalent records in the documented output order.

**AC-03**
Given a column profile identifying a bounded set of observed categorical values and frequencies,
when a compatible profile-driven generator executes,
then the output should use the selected generation policy to reproduce those characteristics within specified tolerances.

**AC-04** *(withdrawn; not applicable. The ID is retained so that other identifiers stay stable.)*

**AC-05**
Given a column group containing city, state and country attributes,
when a compatible generator executes,
then the generated combinations should satisfy the configured geographical consistency rules.

**AC-06**
Given a policy where two column groups have conflicting ownership of one column,
when the generation plan is validated,
then execution should fail before data generation, unless a supported coordination mechanism explicitly resolves the overlap.

**AC-07**
Given a relational generator requiring parent records that are unavailable,
when the execution planner evaluates the dependencies,
then it should either establish a valid generation order or report an actionable dependency error.

**AC-08**
Given two profiling runs against the same table,
when observations are queried,
then the results should be distinguishable by their profiling run and segment.

**AC-09**
Given a dataset generated successfully,
when an independent validation process evaluates its expectations,
then unexpected violations should be reported even if generation completed without execution errors.

**AC-10**
Given a large requested output volume,
when the generation engine executes,
then output should be produced incrementally, with measured memory usage and without requiring all records to be materialised simultaneously.

## Evaluation Strategy

TDF should adopt a requirements-first, evaluation-driven engineering workflow.

Unit, integration and end-to-end tests should verify deterministic functional behaviour.

When coding agents are used, evaluations should assess:

- Requirement satisfaction.
- Correct use of approved architectural decisions.
- Respect for planning and implementation boundaries.
- Unauthorised changes.
- Test quality.
- Implementation correctness.
- Human correction and rework.
- Total model expenditure.

### Data-Generation Evaluations

Generated datasets should be evaluated against relevant quality dimensions:

- Structural correctness.
- Relational integrity.
- Statistical fidelity.
- Scenario coverage.
- Reproducibility.
- Throughput and resource efficiency.

### Learning Evaluations

Future adaptive-generation capabilities should be evaluated using repeatable benchmark datasets.

A successful improvement must demonstrate reduced unexpected generation failures or reduced repair effort without weakening applicable contracts.

## AI-Assisted Engineering Principles

AI coding agents may be used during development, but the TDF runtime should not require an LLM to generate data.

Engineering activities should follow explicit stages:

1. Requirements and acceptance criteria.
2. Domain and architectural modelling.
3. Test-case design.
4. Implementation planning.
5. Human approval.
6. Implementation.
7. Verification and review.

Agents should not begin implementation solely because a plan exists or filesystem permissions allow modification.

Model selection should be based on task complexity, reliability and measured economics.

Where possible, deterministic tools should perform tasks such as code analysis, testing, graph traversal and validation instead of relying on repeated LLM reasoning.

Engineering evaluation should consider cost per accepted task, not merely token consumption.

## Delivery Roadmap

### P1 - Foundational MVP

Goal: Demonstrate deterministic, contract-driven relational generation.

Scope:

- Neo4j ontology and metadata persistence.
- SteelWheels database, table and column registration.
- SteelWheels table relationship representation.
- Basic profiling metrics.
- Generator contracts and policies.
- Column groups.
- Initial deterministic generators.
- CSV output.
- Basic expectation validation.
- CLI.
- SteelWheels sample dataset (`data/steelwheels.duckdb`, `data/*.csv`).
- Automated acceptance tests.

Exit criterion: A developer can generate a reproducible, relationally consistent SteelWheels dataset using a declared contract and validate it from the CLI.

### P2 - Advanced Generation

Goal: Support purpose-specific testing strategies.

Scope:

- Additional functional generators.
- Edge-case and negative-data strategies.
- Statistical and distribution-based generation.
- Larger-volume generation.
- Parquet output.
- More advanced profiling and expectations.
- Improved generation planning.

### P3 - Performance Engineering

Goal: Improve generation throughput and resource efficiency.

Scope:

- Benchmark generation workloads.
- Identify bottlenecks.
- Introduce Rust-based generation kernels where justified.
- Improve streaming and parallel generation.
- Establish reproducible performance benchmarks.

### P4 - Adaptive Quality

Goal: Reduce generation defects through measured improvement.

Scope:

- Failure classification.
- Repair planning.
- Bounded automatic repair.
- Repair history.
- Strategy improvement recommendations.
- Regression evaluation of learned improvements.

### P5 - Extended Test Data Management

Goal: Expand towards a broader open-source TDM platform.

Potential scope:

- Additional database connectors.
- Relational subsetting.
- Masking and privacy-preserving generation.
- Broader dataset provisioning.
- Distributed generation.
- CI/CD integration.
- Additional statistical synthesis methods.

## Open Architectural Decisions

The following decisions remain unresolved and require further design or experimentation.

| ID | Decision |
|--|--|
| AD-001 | Should testing intent be stored on GenerationPolicy or on generator-selection relationships? |
| AD-002 | Should generation policies be reusable between contracts or contract-scoped? |
| AD-003 | How should generator-specific configuration be represented: properties, JSON, or additional graph structures? |
| AD-004 | How should profile segments represent filtering conditions and populations? |
| AD-005 | How should complex profiling observations and distributions be stored? |
| AD-006 | How should composite foreign keys, cyclic dependencies and multiple relationships between tables be modelled? |
| AD-007 | How should expectations identify their target scopes and applicability? |
| AD-008 | How should multiple generators coordinate ownership of overlapping columns? |
| AD-009 | What is the appropriate initial schema for versioning contracts, policies and profiling runs? |
| AD-010 | Which generation operations justify Rust rather than Python or Polars? |
| AD-011 | What is the minimum useful repair mechanism before introducing adaptive learning? |
| AD-012 | What should constitute the stable interface between the Python control plane and future Rust execution components? |
| AD-013 | How should negative testing be represented: as an additional intent, as a policy attribute, or through `EDGE`? |

These decisions must not be silently resolved by coding agents during implementation.

### Phase 1 Provisional Decisions

These decisions apply to Phase 1 only. They are provisional and will be revisited after testing. They do not resolve the open decisions above.

| ID | Provisional Phase 1 position |
|--|--|
| AD-001 | Testing intent is stored as `GenerationPolicy.intent`. |
| AD-002 | Generation policies are scoped to their contract. |
| AD-003 | Generator settings are a `params` JSON property on `ColumnGroup`, validated by Pydantic. |
| AD-004 | One `ProfileSegment` named `ALL` per profile. |
| AD-005 | Value sets and frequencies are stored as inline JSON, capped at 100 distinct values. |
| AD-006 | `RELATES_TO` carries `parent_columns`, `child_columns`, `cardinality` and `optional`. Nullable self-references are generated by ordering rows so each references an earlier row, with the first null. Any other cycle is an error. |
| AD-007 | `Expectation.scope` (TABLE, COLUMN, RELATIONSHIP) plus a `target` reference. |
| AD-008 | Any column overlap between column groups is an error. |
| AD-009 | `version` on contracts; `id` and `created_at` on profiles and runs. |

AD-010 to AD-013 are not addressed in Phase 1.

## Product Success Criteria

The initial product should be considered useful when an engineer can:

- **SC-01:** Register a relational dataset in DuckDB.
- **SC-02:** Profile its tables and columns.
- **SC-03:** Define generation policies and expectations.
- **SC-04:** Generate reproducible synthetic datasets.
- **SC-05:** Preserve declared relational dependencies.
- **SC-06:** Intentionally generate selected negative and edge cases.
- **SC-07:** Validate the generated data against the intended contract.
- **SC-08:** Diagnose failures using meaningful reports.
- **SC-09:** Automate the process through a CLI.
- **SC-10:** Reproduce the workflow locally without paid cloud services.

Longer-term success will be measured through the ability to produce high-quality datasets efficiently and reduce recurring generation failures.

The defining product outcome is not the number of synthetic rows produced. It is the ability to demonstrate that those rows are suitable for the testing objective they were created to support.

## Guiding Principles

- Contracts define quality.
- Profiles provide evidence, not unquestionable truth.
- Policies determine generation behaviour.
- Generators remain replaceable.
- Validation remains independent from generation.
- Intentional violations are first-class testing outcomes.
- Performance is measured using useful, validated output, not raw row counts alone.
- Learned improvements must not weaken approved expectations.
- AI may assist development but should not be a mandatory runtime dependency.
- Engineering begins with requirements and evidence, not with code.
