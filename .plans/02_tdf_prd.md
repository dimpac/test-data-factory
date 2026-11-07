# Plan: TDF PRD and Ontology Update

Source instructions: `.instructions/20261107_02_tdf_prd.md`
Related: `.plans/01_documenting_ontology.md`, `docs/ONTOLOGY.md`, `docs/ontology.mmd`

## 1. Create `docs/PRD.md`

- **Content:** taken from the PRD instructions, with typo and heading fixes. "Usability" moves under the non-functional requirements.
- **Section order:**
  1. Status
  2. Summary
  3. Problem
  4. Objectives
  5. Concepts
  6. Functional requirements
  7. Non-functional requirements
  8. Technology
  9. Acceptance criteria
  10. Evaluation
  11. AI principles
  12. Roadmap
  13. Open decisions
  14. Success criteria
  15. Guiding principles
- **Requirement IDs:**
  - Functional: `FR-META-nn`, `FR-PROF-nn`, `FR-EXP-nn`, `FR-CON-nn`, `FR-GEN-nn`, `FR-VAL-nn`, `FR-CLI-nn`
  - Non-functional: `NFR-PERF-nn`, `NFR-REL-nn`, `NFR-SEC-nn`, `NFR-MAINT-nn`, `NFR-USE-nn`
  - Acceptance criteria `AC-01` to `AC-10`; success criteria `SC-nn`; phases `P1` to `P5`.
  - Existing `AD-001` to `AD-012` keep their IDs.
- **Naming:** use "Generator Contract" throughout, matching the `GeneratorContract` label. Each concept links to its label in `docs/ONTOLOGY.md`.
- **Technology table:** add DuckDB as the local source and sample database for SteelWheels (`data/steelwheels.duckdb`). It is embedded, file-based and already in the development image.
- **New open decision `AD-013`:** how negative testing is represented. AC-04 refers to a "negative generation policy", but the initial intents are only `FUNCTIONAL`, `PERFORMANCE` and `EDGE`. AC-04 cross-references AD-013.

## 2. Update `docs/ontology.mmd` and `docs/ONTOLOGY.md`

**New nodes:**
- `GenerationPlan`: resolved execution instructions.
- `GenerationRun`: one execution, with seed, configuration, outputs and metadata.
- `ValidationResult`: outcome of evaluating one expectation in a run.

**New relationships:**

| Type | From | To |
|---|---|---|
| `RESOLVES` | GenerationPlan | GenerationPolicy |
| `INFORMED_BY` | GenerationPlan | DataProfile |
| `EXECUTES` | GenerationRun | GenerationPlan |
| `HAS_RESULT` | GenerationRun | ValidationResult |
| `EVALUATES` | ValidationResult | Expectation |
| `DERIVED_FROM` | Expectation | ProfileObservation |

**Documented properties (new section):**
- Expectation: `source` in {INFERRED, DECLARED, IMPORTED}; `status` in {PROPOSED, APPROVED, REJECTED, RETIRED}.
- ValidationResult: `outcome` in {SATISFIED, UNEXPECTED_VIOLATION, EXPECTED_VIOLATION, UNEVALUATED}.

**Other `ONTOLOGY.md` changes:**
- Update the diagram, conceptual areas (add an Execution area: Plan, Run, ValidationResult), the summary table and the details.
- Remove the resolved open question about the Expectation-to-profiling link.
- Keep the open question about undefined properties, and link it to the PRD open decisions.

## 3. Update `AGENTS.md`

- Add a `docs/PRD.md` pointer under Project Structure.
- Add a convention: do not resolve PRD open architectural decisions (AD-xxx) without explicit approval.

## 4. Verification

- The Mermaid block in `docs/ONTOLOGY.md` matches `docs/ontology.mmd`, ignoring whitespace.
- Every edge in the diagram has a details entry and a summary-table row.
- No "Generation Contract" remains in `docs/`.
- Requirement IDs are unique.

## Not changed

- `.instructions/` files.
- `docs/steelwheels_erd.mmd`.
- No commit unless requested.
