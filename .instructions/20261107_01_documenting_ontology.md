# Document Test Data Factory Ontology

The Test Data Factory is a contract-driven system for generating synthetic test data.

The ontology represents database structures, generation contracts, policies, generators, data profiles and profiling observations.

The graph acts as the control plane for data generation. Actual generated records are stored outside the knowledge graph. Create a markdown document that will server as reference for this project and will document the ontology described in docs/ontology.mmd with the following nodes and relationships definitions. This document will serve as reference for agents and humans as we progress through the project lifecycle. Save the document as docs/ONTOLOGY.md

## Node Labels

### Database

Represents a source or target database containing tables that may be profiled or used for synthetic data generation.

### Table

Represents a database table. Defines the scope for generation contracts and participates in relationships with other tables.

### Column

Represents a column belonging to a table, including its structural characteristics and data type.

### GenerationContract

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

### HAS_TABLE

Database -> Table

Associates a database with its tables.

### HAS_COLUMN

Table -> Column

Associates a table with its columns.

### RELATES_TO

Table -> Table

Represents a relationship between two tables, including cardinality and the columns used to establish the relationship. May represent foreign-key relationships or other defined associations.

### HAS_GENERATOR_CONTRACT

Table -> GenerationContract

Associates a table with a contract governing the generation of its synthetic data.

### HAS_POLICY

GenerationContract -> GenerationPolicy

Associates a contract with one or more generation policies.

### ENFORCES

GenerationPolicy -> Expectation

Identifies the expectations enforced by a policy, including requirements that may be deliberately violated in negative testing.

### HAS_COLUMN_GROUP

GenerationPolicy -> ColumnGroup

Defines the column groups managed by a generation policy.

### INCLUDES

ColumnGroup -> Column

Identifies the columns belonging to a generation group.

### USES_GENERATOR

ColumnGroup -> Generator

Associates a column group with the generator responsible for producing its values.

### PROFILES

DataProfile -> Table

Identifies the table whose data was analysed by a profile.

### HAS_SEGMENT

DataProfile -> ProfileSegment

Associates a profile with its analysed data populations or segments.

### HAS_OBSERVATION

ProfileSegment -> ProfileObservation

Associates a profile segment with its measured observations.

### ABOUT

ProfileObservation -> Column

Identifies the column to which a profiling observation applies.

### USES_METRIC

ProfileObservation -> ProfileMetric

Identifies the metric used to produce an observation.