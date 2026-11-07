# Test Data Factory Ontology

The Test Data Factory is a contract-driven system for generating synthetic test data.

The ontology represents database structures, generation contracts, policies, generators, data profiles and profiling observations.

The graph acts as the control plane for data generation. Actual generated records are stored outside the knowledge graph.

The diagram source of truth is [`ontology.mmd`](ontology.mmd). Keep this document and that file in sync.

## Diagram

```mermaid
flowchart TD
    A(Database) -->|HAS_TABLE| B(Table)
    B -->|RELATES_TO| B
    B -->|HAS_COLUMN| C(Column)
    B -->|HAS_GENERATOR_CONTRACT| D(GeneratorContract)
    D -->|HAS_POLICY| E(GenerationPolicy)
    E -->|ENFORCES| F(Expectation)
    E -->|HAS_COLUMN_GROUP| G(ColumnGroup)
    G -->|USES_GENERATOR| H(Generator)
    G -->|INCLUDES| C
    I(DataProfile) -->|HAS_SEGMENT| J(ProfileSegment)
    J -->|HAS_OBSERVATION| K(ProfileObservation)
    K -->|USES_METRIC| L(ProfileMetric)
    I -->|PROFILES| B
    K -->|ABOUT| C
```

## Conceptual Areas

- **Schema:** Database, Table, Column
- **Generation:** GeneratorContract, GenerationPolicy, Expectation, ColumnGroup, Generator
- **Profiling:** DataProfile, ProfileSegment, ProfileObservation, ProfileMetric

Table and Column are the shared anchor points. Table links schema to generation (through contracts) and to profiling (through `PROFILES`). Column is referenced by generation (`INCLUDES`) and profiling (`ABOUT`).

## Node Labels

### Database

Represents a source or target database containing tables that may be profiled or used for synthetic data generation.

### Table

Represents a database table. Defines the scope for generation contracts and participates in relationships with other tables.

### Column

Represents a column belonging to a table, including its structural characteristics and data type.

### GeneratorContract

Defines the requirements and intended outcomes for generating synthetic data for a particular table.

### GenerationPolicy

Defines how a generation contract is fulfilled, including applicable expectations and the organisation of generation work into column groups. Policies may vary according to testing intent, such as functional, performance or edge-case testing.

### Expectation

Represents a data-quality or behavioural assertion that generated data must satisfy, or intentionally violate for a specified negative test scenario. May be informed by profiling observations or explicitly defined business rules.

### ColumnGroup

Groups columns that are generated together under a particular policy. Supports correlated attributes and coordinated generation.

### Generator

Represents an executable generation capability or strategy responsible for producing values for a column group. Examples include deterministic, rule-based, statistical and distribution-based generators.

### DataProfile

Represents a profiling result for a table, capturing observed characteristics of source data. A table may have multiple profiles from different profiling runs.

### ProfileSegment

Represents a population or subset of records within a data profile. Allows profiling observations to be associated with specific data populations.

### ProfileObservation

Represents a measured characteristic of a column within a particular profile segment. Stores the observed result of applying a profiling metric.

### ProfileMetric

Defines a reusable profiling measurement, such as null count, distinct non-null count, minimum, maximum, mean or observed value set.

## Relationships

### Summary

| Type | From | To | Description |
|------|------|----|-------------|
| `HAS_TABLE` | Database | Table | Associates a database with its tables. |
| `HAS_COLUMN` | Table | Column | Associates a table with its columns. |
| `RELATES_TO` | Table | Table | Represents a relationship between two tables, including cardinality and the columns used to establish it. May represent foreign-key or other defined associations. |
| `HAS_GENERATOR_CONTRACT` | Table | GeneratorContract | Associates a table with a contract governing the generation of its synthetic data. |
| `HAS_POLICY` | GeneratorContract | GenerationPolicy | Associates a contract with one or more generation policies. |
| `ENFORCES` | GenerationPolicy | Expectation | Identifies the expectations enforced by a policy, including requirements deliberately violated in negative testing. |
| `HAS_COLUMN_GROUP` | GenerationPolicy | ColumnGroup | Defines the column groups managed by a generation policy. |
| `INCLUDES` | ColumnGroup | Column | Identifies the columns belonging to a generation group. |
| `USES_GENERATOR` | ColumnGroup | Generator | Associates a column group with the generator responsible for producing its values. |
| `PROFILES` | DataProfile | Table | Identifies the table whose data was analysed by a profile. |
| `HAS_SEGMENT` | DataProfile | ProfileSegment | Associates a profile with its analysed data populations or segments. |
| `HAS_OBSERVATION` | ProfileSegment | ProfileObservation | Associates a profile segment with its measured observations. |
| `ABOUT` | ProfileObservation | Column | Identifies the column to which a profiling observation applies. |
| `USES_METRIC` | ProfileObservation | ProfileMetric | Identifies the metric used to produce an observation. |

### Details

#### HAS_TABLE

`(:Database)-[:HAS_TABLE]->(:Table)`

Associates a database with its tables.

#### HAS_COLUMN

`(:Table)-[:HAS_COLUMN]->(:Column)`

Associates a table with its columns.

#### RELATES_TO

`(:Table)-[:RELATES_TO]->(:Table)`

Represents a relationship between two tables, including cardinality and the columns used to establish the relationship. May represent foreign-key relationships or other defined associations.

#### HAS_GENERATOR_CONTRACT

`(:Table)-[:HAS_GENERATOR_CONTRACT]->(:GeneratorContract)`

Associates a table with a contract governing the generation of its synthetic data.

#### HAS_POLICY

`(:GeneratorContract)-[:HAS_POLICY]->(:GenerationPolicy)`

Associates a contract with one or more generation policies.

#### ENFORCES

`(:GenerationPolicy)-[:ENFORCES]->(:Expectation)`

Identifies the expectations enforced by a policy, including requirements that may be deliberately violated in negative testing.

#### HAS_COLUMN_GROUP

`(:GenerationPolicy)-[:HAS_COLUMN_GROUP]->(:ColumnGroup)`

Defines the column groups managed by a generation policy.

#### INCLUDES

`(:ColumnGroup)-[:INCLUDES]->(:Column)`

Identifies the columns belonging to a generation group.

#### USES_GENERATOR

`(:ColumnGroup)-[:USES_GENERATOR]->(:Generator)`

Associates a column group with the generator responsible for producing its values.

#### PROFILES

`(:DataProfile)-[:PROFILES]->(:Table)`

Identifies the table whose data was analysed by a profile.

#### HAS_SEGMENT

`(:DataProfile)-[:HAS_SEGMENT]->(:ProfileSegment)`

Associates a profile with its analysed data populations or segments.

#### HAS_OBSERVATION

`(:ProfileSegment)-[:HAS_OBSERVATION]->(:ProfileObservation)`

Associates a profile segment with its measured observations.

#### ABOUT

`(:ProfileObservation)-[:ABOUT]->(:Column)`

Identifies the column to which a profiling observation applies.

#### USES_METRIC

`(:ProfileObservation)-[:USES_METRIC]->(:ProfileMetric)`

Identifies the metric used to produce an observation.

## Conventions

- Node labels are PascalCase; relationship types are UPPER_SNAKE_CASE.
- Relationship directions are as shown in the diagram (for example, `PROFILES` goes from DataProfile to Table).

## Open Questions

- **Expectation and profiling:** Expectation may be informed by profiling observations, but no relationship links Expectation to ProfileObservation or ProfileMetric. Decide whether to model this link.
- **Properties:** node and relationship properties are not yet defined. This includes the cardinality and join columns on `RELATES_TO`.
- **Naming:** the contract node is `GeneratorContract`, but the policy node remains `GenerationPolicy`. Confirm whether the naming should be aligned.
