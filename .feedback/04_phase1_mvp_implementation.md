# Test Data Factory — Engineering Review and Submission Readiness

**Repository:** https://github.com/dimpac/test-data-factory  
**Review scope:** Three-hour technical exercise  
**Priority:** Correctness, reproducibility, verification and reviewer experience

## 1. Objective

Review the current Test Data Factory implementation and improve submission readiness without expanding the original product scope.

The goal is not to finish Test Data Factory. It is to demonstrate sound engineering judgement, explicit requirements, appropriate architecture, safe agent-assisted development and a working, verifiable vertical slice.

**Important:** Inspect the repository before making any changes. Validate every finding below against the current implementation. Do not assume the review is exhaustive or that every potential issue is a confirmed defect.

## 2. Initial Assessment

The repository demonstrates a deliberate engineering approach:

- Containerised development environment.
- Neo4j-backed metadata architecture.
- SteelWheels sample data using DuckDB.
- CLI-first architecture.
- Explicit agent instructions and SKILLs.
- OpenCode and Code Review Graph integration.
- Requirements-first and ontology-driven development.

The principal concern is whether an independent reviewer can quickly discover, execute and verify the implemented functionality.

**Assessment priority: Demonstrate a working solution rather than adding features.**

## 3. P0 — Correctness

### P0.1 — Validate Generator Output Cardinality

**Potential issue**

The generation engine was observed using a pattern equivalent to:

```python
for row, values in zip(rows, group_rows):
    row.update(values)
```

Python's `zip()` silently stops when either iterable is exhausted.

If a generator produces fewer records than requested, incomplete output could remain undetected.

**Required investigation**

- Identify all generator output aggregation paths.
- Determine whether generator cardinality is validated.
- Examine behaviour when a generator returns too few or too many records.
- Check whether missing fields are silently replaced with null values.

**Acceptance criteria**

- Incorrect generator output cardinality cannot silently succeed.
- Failure diagnostics identify the generator, expected count and actual count.
- Tests cover exact, insufficient and excessive output.
- Existing intentional partial-generation semantics, if any, are preserved and documented.

### P0.2 — Validate Referential Integrity

**Potential risk**

Relational generators must preserve parent-child relationships, including composite keys where supported.

**Required investigation**

- Verify that generated foreign keys reference valid parent records.
- Confirm that multiple parent dependencies are handled correctly.
- Determine how empty parent datasets are handled.
- Check generation ordering and cycle detection.
- Confirm that negative-test scenarios can deliberately violate integrity without being mistaken for ordinary generation failures.

**Acceptance criteria**

- Supported relational generation produces valid references.
- Invalid or unsupported dependencies are reported explicitly.
- Tests cover valid, missing and empty parent relationships.
- Unsupported composite-key or cyclic cases are documented rather than silently mishandled.

### P0.3 — Validate Generated Data Against Contracts

**Required investigation**

Trace a complete generation workflow:

1. Load metadata.
2. Resolve the generation contract.
3. Select the applicable policy.
4. Resolve column groups and generators.
5. Generate records.
6. Evaluate applicable expectations.
7. Produce the final result and diagnostics.

**Acceptance criteria**

- At least one supported workflow executes end to end.
- Unexpected validation failures produce a non-success result.
- Intentionally violated expectations are distinguished from defects.
- Unsupported expectations are reported rather than silently treated as passing.

## 4. P1 — Reproducibility and Integration

### P1.1 — Establish One Reproducible Demo

Use a small SteelWheels example.

The reviewer should be able to execute a documented sequence that:

- Starts the necessary local services.
- Loads or initialises required metadata.
- Selects a generation policy.
- Generates a synthetic dataset.
- Validates the generated data.
- Inspects the resulting output and report.

Prefer the existing commands and interfaces. Do not invent a second CLI or parallel demonstration path.

**Acceptance criteria**

A reviewer starting from a clean checkout can reproduce the demonstrated workflow using documented prerequisites and commands.

### P1.2 — Run the Test Suite

Identify the project's existing test commands.

Execute applicable:

- Unit tests.
- Integration tests.
- CLI smoke tests.
- Neo4j integration tests.
- Generator correctness tests.

Record:

- Commands executed.
- Number of tests passing or failing.
- Tests skipped.
- Dependencies unavailable.
- Known limitations.

Do not claim that tests passed unless they were actually executed.

### P1.3 — Verify Container Configuration

Review the development and production container definitions.

Check:

- Non-root execution where appropriate.
- No unnecessary privileged configuration.
- No mounted Docker socket unless explicitly justified.
- No committed credentials.
- Reproducible dependency installation.
- Health and readiness behaviour for dependent services.
- Whether the documented startup commands work from a clean environment.

Focus on demonstrable defects rather than speculative hardening.

## 5. P1 — Performance and Resource Safety

### P1.4 — Review In-Memory Record Materialisation

**Observed implementation pattern**

```python
rows = [{} for _ in range(count)]
```

This creates an in-memory collection proportional to the requested output volume.

**Required investigation**

- Identify the practical memory implications.
- Determine whether output volume is bounded.
- Check behaviour for zero, negative and unusually large requested counts.
- Record the current scaling limitations.

**Recommendation**

Do not undertake a streaming-engine rewrite solely for this assessment.

Implement a small protective limit or useful diagnostic only if required for correctness and safety.

Document future streaming or batch-generation work.

### P1.5 — Review Cartesian Product Materialisation

**Observed implementation pattern**

```python
combinations = list(itertools.product(*pools))
```

This potentially materialises a Cartesian product whose size grows multiplicatively with the number and size of parent key pools.

**Required investigation**

- Determine whether the implementation actually requires complete Cartesian-product enumeration.
- Identify overflow or excessive-memory scenarios.
- Verify behaviour with large key pools.
- Consider lazy sampling or bounded generation as alternatives.

**Acceptance criteria**

At minimum, resource-exhaustion risks are understood and documented. Any implemented correction should preserve deterministic behaviour and relational correctness.

Do not introduce a complicated optimisation without a failing test or measurable justification.

## 6. P1 — Documentation and Reviewer Experience

### P1.6 — Make the README Reflect the Actual Product

**Confirmed documentation issue**

The public README currently opens by describing the repository primarily as a Python development scaffold and hello-world application.

This does not adequately communicate the Test Data Factory concept or its intended engineering demonstration.

Update the README to clearly distinguish existing functionality from proposed capabilities.

Suggested structure:

1. Project overview.
2. Problem being solved.
3. Implemented capabilities.
4. Architecture and ontology.
5. Quick start.
6. End-to-end demonstration.
7. Testing and verification.
8. Agent-assisted engineering workflow.
9. Known limitations.
10. Future roadmap.

The first screen should explain what Test Data Factory does and how to demonstrate it.

### P1.7 — Explain Engineering Decisions

Document the rationale for:

- CLI rather than web UI.
- Neo4j as a metadata control plane.
- Separation of contracts, policies, column groups and generators.
- Independent profiling and expectation management.
- DuckDB and SteelWheels as the local sample data source.
- Devcontainer isolation for coding agents.
- Code Review Graph for source-code context retrieval.
- Deterministic testing and acceptance criteria.

Keep explanations concise. The objective is to expose decisions and trade-offs, not produce a lengthy architecture essay.

### P1.8 — Document Known Limitations

Explicitly identify features not yet complete.

Potential examples, subject to verification:

- In-memory generation.
- Limited generator strategies.
- Incomplete expectation coverage.
- Cyclic foreign-key dependencies.
- Composite foreign-key support.
- Streaming and large-volume generation.
- Automated repair and adaptive learning.
- Statistical synthesis.

Do not describe a feature as implemented merely because the ontology can represent it.

## 7. P2 — Engineering Discipline and Agent Evaluation

### P2.1 — Make the Agent Workflow Explainable

Summarise how coding agents were used.

Include:

- Requirements-first development.
- Explicit planning and implementation boundaries.
- Architecture review before implementation.
- Controlled tool access through a devcontainer.
- Repository SKILLs and instructions.
- Deterministic tests as verification.
- Human review and accountability.

Describe the actual workflow used, not an idealised process that wasn't followed.

### P2.2 — Add a Small Agent Evaluation Example Only If Practical

A useful evaluation case would verify that an agent asked to produce an ontology proposal does not modify implementation files.

Possible checks:

- Required document produced.
- All expected labels included.
- No unexpected repository modifications.
- No source implementation written without approval.

This is optional for the technical submission.

Do not build an evaluation framework unless it is already available and easy to demonstrate.

### P2.3 — Explain Model Selection and Token Efficiency

If supported by actual development evidence, briefly explain:

- Why different tasks may warrant different models.
- How Code Review Graph supports targeted retrieval.
- Why deterministic tools are preferred for verification.
- How unnecessary context and repeated agent calls can be reduced.

Do not claim measured token savings without a baseline and actual usage data.

## 8. Scope Control

The following activities are explicitly out of scope for this review:

- Building a web UI.
- Replacing Neo4j.
- Rewriting the engine in Rust.
- Introducing CTGAN.
- Adding new generation-policy abstractions.
- Implementing autonomous repair.
- Building a comprehensive agent-evaluation platform.
- Refactoring the ontology without evidence of a defect.
- Major performance optimisation unsupported by measurements.

The goal is to make the existing deliverable reliable, understandable and independently verifiable.

## 9. Execution Instructions for the Coding Agent

### Stage 1 — Inspect

Review the current repository and identify:

- Confirmed defects.
- Plausible risks requiring tests.
- Documentation inconsistencies.
- Missing verification evidence.
- Issues irrelevant to the submission.

Provide exact file references and line numbers for findings.

### Stage 2 — Prioritise

Produce a concise plan ordered by:

1. Correctness defects.
2. Reproducibility blockers.
3. Verification gaps.
4. Submission documentation.
5. Optional improvements.

For each task, include expected outcome, estimated complexity and verification method.

### Stage 3 — Approval Gate

**Stop after producing the plan.**

Do not modify implementation files, tests, configuration or documentation until explicitly authorised.

Permission to edit files is not permission to implement.

### Stage 4 — Implementation (Only After Approval)

When authorised:

- Implement only the approved scope.
- Prefer small, independently verifiable changes.
- Add regression tests for confirmed defects.
- Preserve existing architecture unless changes are approved.
- Run relevant tests after modifications.
- Record any unresolved problems.

If an architectural assumption proves invalid, stop and request a new decision.

## 10. Final Review Deliverables

Produce:

1. **Findings report** — confirmed issues, severity and evidence.
2. **Remediation plan** — ordered changes with acceptance criteria.
3. **Verification report** — commands run and observed results.
4. **Submission readiness checklist** — passed, failed, blocked or not evaluated.
5. **Known limitations** — honest description of what the implementation does not yet support.

## 11. Definition of Done

The review is complete when:

- The implemented capabilities are accurately documented.
- A representative workflow can be reproduced or its blockers are explicitly identified.
- Critical correctness risks have been tested.
- The test outcomes are reported accurately.
- The repository is understandable to a reviewer unfamiliar with the project.
- No unapproved architectural changes have been introduced.
- The three-hour development scope remains distinguishable from subsequent improvement work.

**Final principle:**

The submission should demonstrate not how much software an agent can produce, but how effectively an engineer can define, direct, constrain and verify agent-assisted software development.
