# Plan: Document the Test Data Factory Ontology

Source instructions: `.instructions/20261107_01_documenting_ontology.md`
Source diagram: `docs/ontology.mmd`

## Decisions

- The contract node label is `GeneratorContract` (renamed from `GenerationContract`).
- The relationship `HAS_GENERATOR_CONTRACT` (Table -> GeneratorContract) keeps its name.
- The policy node stays `GenerationPolicy`.
- The gap between Expectation and profiling is recorded as an open question, not modelled.
- `AGENTS.md` gets a pointer to the new document.

## Steps

### 1. Create `docs/ONTOLOGY.md`

- **Overview:** contract-driven synthetic data generation. The graph is the control plane; generated records are stored outside it.
- **Diagram:** Mermaid block copied from `docs/ontology.mmd`. The `.mmd` file is the source of truth.
- **Conceptual areas:**
  - Schema: Database, Table, Column
  - Generation: GeneratorContract, GenerationPolicy, Expectation, ColumnGroup, Generator
  - Profiling: DataProfile, ProfileSegment, ProfileObservation, ProfileMetric
  - Table and Column are the shared anchor points.
- **Node labels:** one subsection per label, with the definitions from the instructions verbatim (`GenerationContract` documented as `GeneratorContract`).
- **Relationships:**
  - Summary table: Type, From, To, Description.
  - One subsection per relationship with its `(:From)-[:TYPE]->(:To)` pattern and definition.
- **Conventions:**
  - Labels are PascalCase; relationship types are UPPER_SNAKE_CASE.
  - Directions match the diagram (e.g. `PROFILES` goes DataProfile -> Table).
  - Keep `ONTOLOGY.md` and `ontology.mmd` in sync.
- **Open questions:**
  - Expectation "may be informed by profiling observations", but no relationship links Expectation to ProfileObservation or ProfileMetric.
  - Node and relationship properties are not defined (including cardinality and join columns on `RELATES_TO`).

### 2. Update `docs/ontology.mmd`

- Line 5: `D(GenerationContract)` -> `D(GeneratorContract)`.

### 3. Update `AGENTS.md`

- Under "Project Structure", add:
  ``- `docs/ONTOLOGY.md`: reference for the Test Data Factory graph ontology (node labels and relationships); diagram source in `docs/ontology.mmd`.``

## Not changed

- `.instructions/20261107_01_documenting_ontology.md` remains as the original prompt.

## Verification

- `grep -rn GenerationContract docs AGENTS.md` returns no matches (only the historical instruction file retains it).
- `docs/ONTOLOGY.md` lists all 12 node labels and all 14 relationship types from the instructions.
- The Mermaid block in `docs/ONTOLOGY.md` matches `docs/ontology.mmd`.
