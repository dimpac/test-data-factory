# Test Data Factory — Assessment Final Compliance Review

**Repository:** https://github.com/dimpac/test-data-factory  
**Task type:** Final engineering review, submission remediation and repository cleanup  
**Priority:** Submission correctness, reproducibility and evidence  
**Implementation authority:** Limited to the scope defined below

## 1. Objective

Review the current Test Data Factory repository against the rubric and remediate identified submission gaps.

The primary goal is to demonstrate one meaningful, locally executable, independently verifiable end-to-end workflow, supported by concise evidence of sound engineering practices.

This is not an opportunity to expand the Test Data Factory product roadmap.

**Do not add new features unless they are strictly necessary to make the selected end-to-end workflow operational.**

## 2. Mandatory Initial Inspection

Start by inspecting the current local repository, not merely the public GitHub version.

Review:

- Current Git status, commit history and uncommitted changes.
- README and TUTORIAL.md.
- Production Dockerfile and Docker Compose configuration.
- Actual CLI commands.
- Existing source code and automated tests.
- SteelWheels sample data.
- Generation contracts, policies, generators and expectations.
- Existing evidence documents.
- Agent configuration and development instructions.

Identify changes made by previous agents and avoid overwriting them.

Produce a short compliance assessment before implementing fixes.

Classify every requirement as:

- **PASS:** Verified through execution or direct repository evidence.
- **PARTIAL:** Implemented but missing necessary evidence or coverage.
- **FAIL:** Verified defect or missing mandatory capability.
- **UNVERIFIED:** Could not establish whether the requirement is satisfied.

Do not treat code inspection alone as proof that an end-to-end workflow executes successfully.

## 3. Mandatory Repository Cleanup

### CLEAN-001 — Remove Hello-World Python Application

Remove the obsolete application at:

`apps/hello-world/`

Remove associated:

- Python packaging configuration.
- Entry points and console scripts.
- Tests and fixtures specific to hello-world.
- Docker or Compose references.
- Dependency references.
- README instructions.
- Build scripts referencing the deleted application.

Preserve shared libraries and dependencies still required by TDF.

After removal, the repository must build and run without the hello-world application.

### CLEAN-002 — Remove Hello-World Agent SKILL

Remove:

`.claude/skills/00-hello-world/`

Remove obsolete references to this skill from agent instructions, documentation and configuration.

Do not delete or modify other agent instructions or SKILLs unless they directly depend on the removed example.

**Do not create replacement SKILLs.**

### CLEAN-003 — Verify Cleanup

Search the repository for references to:

- `hello-world`
- `hello_world`
- `00-hello-world`

Remove obsolete references while preserving legitimate historical records or unrelated text.

Do not rewrite Git history.

## 4. Rubric Compliance

### R-001 — Meaningful End-to-End Workflow

Demonstrate one working SteelWheels workflow using the actual application.

The preferred workflow is:

1. Start required services.
2. Register or initialise SteelWheels metadata.
3. Profile a supported table.
4. Retrieve or configure a generation contract.
5. Resolve the applicable policy and generators.
6. Generate synthetic records.
7. Validate the generated dataset.
8. Inspect the output.

Use the existing public CLI.

If the complete workflow is not supported, identify the smallest coherent vertical slice that genuinely works and explain the limitations.

Do not simulate missing functionality with undocumented Neo4j mutations or fabricated CLI commands.

**Acceptance criterion:** The selected workflow produces a real output and a verifiable result.

### R-002 — Full-Stack Ownership

Confirm the demonstrated solution includes all necessary local components:

- Application code.
- Runtime container.
- Neo4j backing service.
- SteelWheels sample data and DuckDB where required.
- Configuration.
- Generated output.
- Tests and verification.

No browser UI is necessary.

**Acceptance criterion:** The workflow runs locally without reliance on paid services, private repositories or assessor-specific infrastructure.

### R-003 — Docker Packaging

Verify the production container:

- Builds successfully.
- Executes the real TDF CLI.
- Contains required runtime dependencies.
- Does not require development tooling.
- Uses an appropriate non-root user.
- Connects to Neo4j through Docker networking.
- Supports documented input/output volumes.
- Does not contain embedded secrets.
- Does not require privileged execution.

Preserve the existing devcontainer setup.

Do not introduce new infrastructure unless essential.

### R-004 — README and TUTORIAL.md

Review Haiku's completed tutorial critically.

Verify that every command corresponds to an implemented CLI capability.

The README must provide:

- What TDF does.
- Prerequisites.
- Quick start.
- One example workflow.
- Test/verification command.
- Known limitations.
- Link to TUTORIAL.md.
- Link to the evidence pack.

The tutorial should provide the detailed SteelWheels walkthrough.

Remove any remaining description of the project as a hello-world scaffold.

**Acceptance criterion:** A developer unfamiliar with TDF can follow the instructions without undocumented intervention.

### R-005 — Build, Test and Verify

Identify or create one simple verification entry point.

Prefer an existing Makefile or script if available.

The entry point must execute the appropriate checks, report failures and return a nonzero exit code when a mandatory check fails.

Include:

- Relevant unit tests.
- CLI smoke testing.
- Contract validation checks.
- A representative generation test.
- Referential integrity validation where supported.

Distinguish between fast checks suitable for every PR and integration tests requiring Docker services.

Do not build an elaborate testing framework.

### R-006 — Safe Failure Handling

Demonstrate at least one intentional, controlled failure.

Suitable examples:

- Invalid GenerationContract.
- Unknown generator.
- Conflicting ColumnGroup ownership.
- Missing required metadata.
- Invalid foreign-key dependency.
- Expectation validation rejection.

Use an existing supported case where possible.

The failure must:

- Be detected.
- Produce an understandable diagnostic.
- Return an appropriate failure status.
- Avoid reporting incomplete output as successful.

Include a regression test or repeatable verification command.

### R-007 — Configuration and Operational Thinking

Review how TDF handles:

- Environment variables.
- Neo4j credentials.
- Connection failures.
- Startup readiness.
- Input/output directories.
- Logging and diagnostic messages.
- Partial or failed generation runs.
- Cleanup and recovery.

Document the supported operational procedures.

Do not implement a new observability platform.

### R-008 — CI/CD and Cloud Promotion

Provide a concise explanation of how TDF would move from a local Docker-based solution to enterprise CI/CD.

Cover:

1. Pull-request validation.
2. Unit and integration testing.
3. Container image build.
4. Dependency and vulnerability scanning.
5. Versioned artifact publication.
6. Container registry.
7. Deployment to a cloud execution environment.
8. Environment-specific configuration and secret management.
9. Operational monitoring.
10. Promotion and rollback.

An actual cloud deployment is not required.

Do not invent infrastructure that has already been provisioned.

### R-009 — Engineering Evidence Pack

Create or complete a concise `evidence/` directory.

Use the following structure unless equivalent documents already exist:

**`evidence/intent.md`**

Describe the problem, intended users, assumptions, constraints, exclusions and success criteria.

**`evidence/design.md`**

Describe the implemented architecture, components, data flow, ontology, key trade-offs, security considerations and future production shape.

Reference existing Mermaid diagrams where appropriate.

Do not introduce a new architectural design purely for presentation.

**`evidence/agentic-workflow.md`**

Document the actual AI-assisted development process.

Include:

- Models and agent tools used, where known.
- Requirements-first approach.
- Architectural exploration and planning.
- Separation between planning and implementation.
- Human approval and review.
- Use of Code Review Graph.
- How work was delegated.
- How agent output was verified.
- Representative interventions and corrections.
- Known limitations of the agent workflow.

Do not invent prompts, decisions, token savings or human interventions.

Where historical information is unavailable, mark it as requiring human input.

**`evidence/verify.md`**

Document:

- Test commands.
- Observed test results.
- Build verification.
- End-to-end workflow results.
- Controlled failure scenario.
- Known gaps.
- Proposed CI checks.

Separate verified results from unexecuted recommendations.

**`evidence/operate.md`**

Provide concise operational instructions, including:

- Startup and shutdown.
- Logs and diagnostics.
- Configuration and secrets.
- Known failure modes.
- Troubleshooting.
- Recovery.
- Local-to-cloud operational considerations.

**`evidence/decisions.md`**

Document three to five meaningful engineering decisions.

Prioritise:

- CLI-first architecture rather than a web UI.
- Neo4j as a metadata control plane.
- Contract and policy separation.
- Requirements-first and test-driven agent implementation.
- Deliberate limitations of the three-hour MVP.

Explain alternatives, rationale, consequences and accepted trade-offs.

Keep the evidence pack concise. Avoid duplicating the PRD or TUTORIAL.md.

### R-010 — Git History

Inspect the current commit history.

Verify that the repository contains meaningful incremental commits.

Do not:

- Squash commits.
- Rewrite history.
- Modify commit timestamps.
- Manufacture a development timeline.
- Misrepresent work completed after the original timebox.

If the repository includes post-timebox changes, preserve their actual provenance.

Do not commit or push changes unless explicitly authorised.

## 5. Quality Review

Inspect the implemented core workflow for critical correctness problems.

Prioritise:

- Silent incomplete generator output.
- Unexpected null values.
- Broken referential integrity.
- Invalid generation ordering.
- Incorrect expectation validation.
- Unhandled configuration errors.
- Inaccurate success reporting.

Do not attempt to fix every possible data-quality limitation.

For each proposed correction, establish:

1. A reproducible failure.
2. An expected result.
3. A narrowly scoped fix.
4. A regression test.

If the issue requires a significant redesign or a new product capability, document it as a known limitation rather than implementing it.

## 6. Out of Scope

Do not:

- Add CTGAN or statistical synthesis.
- Introduce Rust.
- Implement autonomous data repair.
- Redesign the ontology.
- Add a web UI.
- Add agent SKILLs.
- Introduce additional orchestration frameworks.
- Change the generator architecture without an identified defect.
- Expand the testing-intent catalogue.
- Build a comprehensive benchmark platform.
- Add unrelated abstractions or refactorings.

**The objective is submission readiness, not product completeness.**

## 7. Verification Procedure

After approved changes:

1. Build the production Docker image.
2. Start the required services in an isolated environment.
3. Execute the documented SteelWheels workflow.
4. Verify generated outputs.
5. Run expectation validation.
6. Execute a controlled failure scenario.
7. Run the automated tests.
8. Confirm obsolete hello-world components are removed.
9. Verify README and TUTORIAL.md commands.
10. Inspect Git status and the final diff.

Do not claim success for commands that were not executed.

If Docker or another dependency is unavailable, document the blocker explicitly.

Avoid destructive operations on existing developer volumes or unrelated host files.

## 8. Definition of Done

The submission is ready when:

- A meaningful end-to-end workflow is demonstrated.
- The production Docker image builds and runs.
- An independent reviewer can execute the documented workflow.
- One verification entry point exists.
- Appropriate automated tests pass.
- A controlled failure is demonstrated.
- Basic configuration and operational handling are documented.
- The six evidence documents exist and accurately describe the system.
- README and TUTORIAL.md are consistent with the implementation.
- The hello-world Python application and agent skill are removed.
- Existing development workflows remain functional.
- Git history is preserved.
- Known limitations are explicitly documented.

## 9. Final Report

Provide a short compliance matrix with each requirement marked PASS, PARTIAL, FAIL or UNVERIFIED.

Include:

- Files modified or deleted.
- Confirmed defects and fixes.
- Docker build outcome.
- Test results.
- End-to-end verification results.
- Controlled failure evidence.
- Documentation and evidence-pack status.
- Outstanding risks.
- Final Git status.

Do not declare overall compliance if any mandatory requirement remains unverified.

## 10. Engineering Instructions

You are authorised to perform repository cleanup, documentation improvements, packaging fixes and narrowly scoped corrections to the existing end-to-end workflow.

For significant architectural changes or new product capabilities, stop and request approval.

Keep every change proportionate to the assessment.

**The finished repository should demonstrate disciplined engineering ownership, not an artificially polished or overbuilt three-hour MVP.**
