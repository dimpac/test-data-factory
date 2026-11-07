# Test Data Factory — SteelWheels End-to-End Tutorial

This tutorial takes you from a clean checkout to validated synthetic data for the SteelWheels
sample database, using the production Docker image and the `tdf` CLI. Every command below was run
against a disposable Compose project before publication.

Commands are shown for a POSIX shell (Linux, macOS, WSL, or Git Bash). In PowerShell, run them
unchanged except for the `export` lines, which you can replace with `$env:` assignments.

> **Honest scope.** The CLI can register metadata, load contracts, profile tables, generate CSV and
> validate CSV. It has **no** commands to list or show metadata, profiles, policies, column groups or
> expectations. Those are inspected with read-only Cypher in Neo4j Browser (Step 13). Policies, column
> groups, generators and expectations are configured by editing a contract YAML file, not with CLI
> flags. See [Known limitations](#known-limitations).

## Step 1 — Prerequisites

| Requirement | Notes |
|---|---|
| Docker Engine or Docker Desktop with Compose v2 | `docker compose version` must work. |
| Git | To clone the repository. |
| Ports 17474 and 17687 free on `127.0.0.1` | Override with `TDF_NEO4J_HTTP_PORT` and `TDF_NEO4J_BOLT_PORT`. |

Supported environment: Docker on Linux, macOS, or Windows (WSL 2 backend). The Neo4j image is
`linux/amd64`. On Apple Silicon, Docker runs it under emulation, which is slower but works.

Neo4j Enterprise is used because the TDF test suite and the Compose setup already rely on it. The
image is pinned to `neo4j:5.26-enterprise`, and the license agreement is accepted by the Compose
file (`NEO4J_ACCEPT_LICENSE_AGREEMENT=yes`). Review the Neo4j license terms before using it outside
evaluation.

Configuration: copy the environment template and set a password. **Never commit `.env`.**

```bash
git clone <repository-url> test-data-factory
cd test-data-factory
cp .env.changeme .env
```

Edit `.env` and set a non-empty `NEO4J_PASSWORD`. Leave the other values as they are:

| Variable | Used by | Purpose |
|---|---|---|
| `NEO4J_USERNAME` | Neo4j, CLI | Neo4j user (`neo4j`). |
| `NEO4J_PASSWORD` | Neo4j, CLI | Required. Applied when the Neo4j data volume is first created. |
| `NEO4J_DATABASE` | Neo4j, CLI | Database name (`test-data-factory`). |
| `NEO4J_URL` | CLI | Overridden inside Compose to `bolt://neo4j:7687`. |

Optional host ports (defaults shown):

```bash
export TDF_NEO4J_HTTP_PORT=17474
export TDF_NEO4J_BOLT_PORT=17687
```

Output directory: generated CSV files are written to `./out` on the host. Create it first so it is
owned by your user:

```bash
mkdir -p out
```

> On Linux, the container runs as UID 1000. If your host user is not UID 1000, make `out` writable
> by that user, for example `sudo chown 1000:1000 out`. Docker Desktop on Windows and macOS does
> not need this.

## Step 2 — Build the Docker Image

The `tdf` image is built from the root `Dockerfile`. It installs only the runtime dependencies
pinned in `requirements.txt`, builds the SteelWheels DuckDB from the committed CSV files, and runs
as the non-root user `tdf` (UID 1000). It contains no tests, git, or coding-agent tooling.

```bash
docker compose build tdf
```

Verify the image and the CLI:

```bash
docker image inspect test-data-factory-tdf:local --format '{{.Config.User}} {{.Config.Entrypoint}}'
docker compose run --rm tdf --help
```

Expected: the first line prints `tdf [tdf]`. The help output lists
the commands `contract`, `generate`, `metadata`, `profile`, `repair`, `report` and `validate`.

## Step 3 — Start Neo4j

Start only the database service in the background:

```bash
docker compose up -d neo4j
```

Wait until the health check reports `healthy`:

```bash
docker compose ps neo4j
```

Expected: `STATUS` shows `Up ... (healthy)`. This takes about 20–40 seconds on first start.

Verify that the database accepts queries. This command reads `.env` on the host, so you do not need to
type the password:

```bash
set -a; . ./.env; set +a
docker compose exec -T neo4j cypher-shell -u "$NEO4J_USERNAME" -p "$NEO4J_PASSWORD" -d "$NEO4J_DATABASE" "RETURN 'ready' AS status;"
```

Expected output:

```text
status
"ready"
```

**Neo4j Browser:** open <http://localhost:17474> (or your `TDF_NEO4J_HTTP_PORT`). Sign in with
`NEO4J_USERNAME` and `NEO4J_PASSWORD` from `.env`, and set the database to `test-data-factory` with
`:use test-data-factory` if it is not already selected.

Neo4j data is stored in the named volume `tdf-neo4j-data`. Your data survives `docker compose down`
and is removed only by `docker compose down -v` (see Step 14).

> **Password changes.** `NEO4J_AUTH` is applied only when the data volume is first initialised. If
> you change `NEO4J_PASSWORD` later, either restore the old value or remove the volume with
> `docker compose down -v` and start again.

## Step 4 — Inspect SteelWheels

SteelWheels is a sample sales dataset: customers place orders, orders contain order lines for
products, and customers are assigned to sales representatives who work in offices. The raw data is in
`data/*.csv`. The CLI reads the **built** DuckDB file, which the Docker build produces at
`/opt/tdf/data/steelwheels.duckdb` inside the image. You do not need to run anything on the host.

The schema is declared in `docs/steelwheels_erd.mmd`. It defines 6 tables and 6 relationships:

| Table | Rows | Columns | Primary key | Foreign keys |
|---|---:|---:|---|---|
| `offices` | 7 | 9 | `OFFICECODE` | — |
| `employees` | 23 | 8 | `EMPLOYEENUMBER` | `OFFICECODE` → `offices`; `REPORTSTO` → `employees` (self) |
| `customers` | 126 | 13 | `CUSTOMERNUMBER` | `SALESREPEMPLOYEENUMBER` → `employees` |
| `orders` | 330 | 7 | `ORDERNUMBER` | `CUSTOMERNUMBER` → `customers` |
| `orderdetails` | 3001 | 5 | `ORDERNUMBER`, `PRODUCTCODE` (composite) | `ORDERNUMBER` → `orders`; `PRODUCTCODE` → `products` |
| `products` | 110 | 9 | `PRODUCTCODE` | — |

Row counts are the source CSV row counts. Column counts match the registered schema (verified in Step 5).

The ERD is the file you pass to `metadata register` in Step 5. The row counts are useful later when
you check generated output.

## Step 5 — Register the Database

Registering reads the Mermaid ERD, checks the DuckDB physical schema against it, and writes the
database, tables, columns and relationships to Neo4j. Run this from the repository root:

```bash
docker compose run --rm tdf metadata register \
  --database steelwheels \
  --erd docs/steelwheels_erd.mmd \
  --source data/steelwheels.duckdb
```

> The `tdf` service mounts the repository's `./out` directory only. Paths such as `docs/...` and
> `data/...` are resolved **inside the image**, under `/opt/tdf`, where the same files are bundled.
> Paths are therefore the same as in the repository.

Expected output:

```text
Registered steelwheels
```

Verify in Neo4j (Browser, or `cypher-shell` as in Step 3). This returns one row per table; the
column counts sum to 51:

```cypher
MATCH (d:Database {name: 'steelwheels'})-[:HAS_TABLE]->(t:Table)-[:HAS_COLUMN]->(c:Column)
RETURN t.name AS table, count(c) AS columns
ORDER BY table;
```

Expected:

| table | columns |
|---|---:|
| customers | 13 |
| employees | 8 |
| offices | 9 |
| orderdetails | 5 |
| orders | 7 |
| products | 9 |

Relationships. In the graph, `RELATES_TO` runs from the parent table to the child table, and its
`parent_columns` and `child_columns` properties record the join columns:

```cypher
MATCH (parent:Table)-[r:RELATES_TO]->(child:Table)
RETURN parent.name AS parent, child.name AS child,
       r.parent_columns AS parent_columns, r.child_columns AS child_columns,
       r.cardinality AS cardinality
ORDER BY parent, child;
```

Expected: six rows, including `customers → orders` on `CUSTOMERNUMBER`,
`employees → employees` on `EMPLOYEENUMBER` → `REPORTSTO` (self-reference), and
`orders → orderdetails` on `ORDERNUMBER`.

## Step 6 — Profile the Data

Profiling reads a table from DuckDB, computes metrics per column, and stores them in Neo4j. One
table is profiled per command. Profiling reads options such as `value_set` from the stored contract, so **run the contract load in
Step 7 before profiling**. Then profile each table:

```bash
docker compose run --rm tdf profile --database steelwheels --source data/steelwheels.duckdb --table products
docker compose run --rm tdf profile --database steelwheels --source data/steelwheels.duckdb --table orders
docker compose run --rm tdf profile --database steelwheels --source data/steelwheels.duckdb --table customers
docker compose run --rm tdf profile --database steelwheels --source data/steelwheels.duckdb --table employees
docker compose run --rm tdf profile --database steelwheels --source data/steelwheels.duckdb --table offices
docker compose run --rm tdf profile --database steelwheels --source data/steelwheels.duckdb --table orderdetails
```

Expected for each: `Profiled <table>: <32-character profile id>`.

Metrics recorded per column are `row_count`, `null_count`, `non_null_count`,
`distinct_non_null_count`, `min`, `max`, `mean`, `stddev`, `value_set` and `value_frequencies`.
`value_set` is recorded only for low-cardinality columns (up to 100 distinct values).

Inspect the observations. This shows one row per table with the number of observations:

```cypher
MATCH (t:Table)<-[:PROFILES]-(dp:DataProfile)-[:HAS_SEGMENT]->(:ProfileSegment)-[:HAS_OBSERVATION]->(o:ProfileObservation)
RETURN t.name AS table, count(DISTINCT o) AS observations
ORDER BY table;
```

Expected row counts: `customers` 76, `employees` 54, `offices` 56, `orderdetails` 36,
`orders` 40, `products` 56. The total is 318.

Look at the observed values for `orders.STATUS`, which generation uses for its enumeration:

```cypher
MATCH (c:Column {table: 'orders', name: 'STATUS'})<-[:ABOUT]-(o:ProfileObservation)-[:USES_METRIC]->(m:ProfileMetric)
RETURN m.name AS metric, o.value_json AS value
ORDER BY metric;
```

Expected `value_set`: `["Cancelled", "Disputed", "In Process", "On Hold", "Resolved", "Shipped"]`.
`value_frequencies` shows `Shipped` at 307 of 330 rows.

**How observations inform generation.** Profiling does not generate anything by itself. A contract
column that declares `params: {source: profile}` (for example `orders.STATUS`, `products.PRODUCTLINE`)
takes its categories from the stored `value_set`. Generation then produces values that match the
observed categories, and validation (Step 12) checks the output against the same profile. The
profile also records the source's null rates and ranges, which you can compare with generated
output.

## Step 7 — Create a Generation Contract

The contract is a YAML file. Each contract names one table, its policies, column groups and
expectations. The bundled SteelWheels contract is at `config/steelwheels/contract.yaml` inside the
image (`libs/tdf/config/steelwheels/contract.yaml` in the repository). It has six contracts, one per
table.

Load it into Neo4j:

```bash
docker compose run --rm tdf contract load config/steelwheels/contract.yaml
```

Expected output:

```text
Loaded 6 contracts
```

The loader checks each contract against the schema registered in Step 5. Verify the contract
association for each table:

```cypher
MATCH (t:Table)-[:HAS_GENERATOR_CONTRACT]->(gc:GeneratorContract)
RETURN t.name AS table, gc.id AS contract
ORDER BY table;
```

Expected: six rows, for example `customers` → `steelwheels:customers:1`. The contract id is
`<database>:<table>:<version>`.

The `tdf` container only sees files baked into the image (under `/opt/tdf`) and the `./out` mount.
To load a modified contract, you must mount it into the container, for example by adding a
`./my-contracts:/opt/tdf/my-contracts:ro` volume to the `tdf` service in `compose.yaml`. This tutorial
does not do that; it loads the bundled contract only.

## Step 8 — Configure a Generation Policy

Each contract has one or more policies. A policy has an `intent`, a `row_count` and the column
groups and expectations that apply to it. The supported intents are `FUNCTIONAL`, `PERFORMANCE` and
`EDGE`. Only `FUNCTIONAL` is used by `generate` and `validate` in this release.

The SteelWheels contract uses a functional policy on each table, for example:

```yaml
    policies:
      - name: orders_functional
        intent: FUNCTIONAL
        row_count: 330
```

`row_count` is the number of rows to generate for that table. You can override it per table at
generation time with `--rows TABLE=COUNT` (Step 11).

Verify the policies in Neo4j:

```cypher
MATCH (t:Table)-[:HAS_GENERATOR_CONTRACT]->(:GeneratorContract)-[:HAS_POLICY]->(p:GenerationPolicy)
RETURN t.name AS table, p.name AS policy, p.intent AS intent, p.row_count AS row_count
ORDER BY table;
```

Expected: six rows, all with `intent` `FUNCTIONAL`; `customers` has `row_count` 126 and `orderdetails`
has 3001.

## Step 9 — Configure Column Groups and Generators

A column group binds one or more columns to one generator. Columns in a group are generated together,
so related values stay consistent. A column can belong to only one group.

The `location` group on `customers` is an example of coordinated generation. It binds `CITY`, `STATE`,
`POSTALCODE` and `COUNTRY` to the `geo` generator, which draws a whole city, state and postal code
from one postal-code row in `data/allCountriesCSV.csv.gz`. The four values always belong to the same
place:

```yaml
          - name: location
            columns: [CITY, STATE, POSTALCODE, COUNTRY]
            generator: geo
            params: {source: data/allCountriesCSV.csv.gz, countries: [Australia, ...]}
```

Supported generators: `sequence`, `integer`, `float`, `string`, `boolean`, `date`, `timestamp`,
`categorical`, `tuple`, `foreign_key`, `faker` and `geo`.

Verify the groups and generators in Neo4j:

```cypher
MATCH (p:GenerationPolicy {name: 'customers_functional'})-[:HAS_COLUMN_GROUP]->(g:ColumnGroup)-[:USES_GENERATOR]->(gen:Generator)
RETURN g.name AS column_group, gen.name AS generator
ORDER BY column_group;
```

Expected: `address_line1` → `faker`, `location` → `geo`, `sales_rep` → `foreign_key`, `key` → `sequence`,
and so on for the other groups in that policy.

The `foreign_key` generator on `customers.SALESREPEMPLOYEENUMBER` sets `null_ratio: 0.17`, so about
17 % of generated customers have no sales representative.

## Step 10 — Define Expectations

Expectations are declared checks that must hold for the generated data. Each has an `id`, a `type`,
a `scope`, a `target` and optional `params`. The types evaluated by `validate` are `completeness`,
`uniqueness`, `range`, `enumeration`, `volume`, `referential_integrity` and `tuple_in_set`.

Two examples from the bundled contract:

```yaml
- {id: orders_status_enum, type: enumeration, scope: COLUMN, target: {table: orders, columns: [STATUS]}, params: {source: profile}}
- {id: customers_rep_fk, type: referential_integrity, scope: RELATIONSHIP, target: {table: customers, columns: [SALESREPEMPLOYEENUMBER]}, params: {parent: employees, parent_columns: [EMPLOYEENUMBER]}}
```

Expectations are stored on the policy, so they are associated with the generation policy they belong
to. Verify this in Neo4j:

```cypher
MATCH (p:GenerationPolicy)-[:ENFORCES]->(e:Expectation)
RETURN p.name AS policy, e.id AS expectation, e.type AS type, e.status AS status
ORDER BY policy, expectation;
```

Expected: 15 rows in total, all with `status` `APPROVED`.

**Profiling observations versus generation requirements.** A profile observation is a measurement of
the source data (for example, "`STATUS` has six distinct values and `Shipped` is 307 of 330 rows").
It is evidence, not a rule. An expectation is a requirement the generated output must meet (for
example, "every `STATUS` value is in the approved set"). Expectations with `source: profile` take
their allowed values from observations, so the two are linked, but the expectation is what
`validate` enforces.

## Step 11 — Generate Synthetic Data

Generation reads the stored contracts and profiles from Neo4j, generates rows in foreign-key order,
and writes one CSV file per table. Use an explicit seed for reproducible output. The seed defaults to
42, and the command below sets it explicitly:

```bash
docker compose run --rm tdf generate --database steelwheels --seed 42 --out /out/steelwheels
```

Expected output:

```text
Generated 3597 rows in /out/steelwheels
```

The output directory `/out` inside the container is the `./out` directory on the host. The files are
at `./out/steelwheels/` and are readable from the host:

```bash
ls -l out/steelwheels
```

Expected files: `customers.csv`, `employees.csv`, `offices.csv`, `orderdetails.csv`, `orders.csv`
and `products.csv`.

Look at a small sample:

```bash
head -4 out/steelwheels/customers.csv
```

The generated values are synthetic (for example, `Dominguez-Cooper` and `Vargas`). Their structure
matches the source: the same columns, the same keys and postal codes from the geo source.

**Seed reproducibility.** The same seed produces identical files. You can check this:

```bash
docker compose run --rm tdf generate --database steelwheels --seed 42 --out /out/repeat
diff -r out/steelwheels out/repeat && echo "identical"
rm -rf out/repeat
```

Expected: `identical`.

**Row count override.** `--rows TABLE=COUNT` changes the row count for one table. Use it with care:
foreign keys reference parents, so changing a parent's count changes which child values are valid.
The following example makes a small, self-consistent dataset:

```bash
docker compose run --rm tdf generate --database steelwheels --seed 7 --out /out/small --rows orders=50 --rows orderdetails=50
```

Expected: `Generated 366 rows in /out/small`. Remove it afterwards with `rm -rf out/small`.

## Step 12 — Validate the Generated Data

Validation reads the generated CSV files and checks them against the FUNCTIONAL expectations stored
in Neo4j. It is independent of generation and can be run on any directory of CSV files:

```bash
docker compose run --rm tdf validate --database steelwheels --data-dir /out/steelwheels
```

Expected output (15 lines, all `SATISFIED`):

```text
customers_pk_unique: SATISFIED
customers_rep_fk: SATISFIED
orders_pk_unique: SATISFIED
orders_status_enum: SATISFIED
orders_customer_fk: SATISFIED
products_pk_unique: SATISFIED
products_line_enum: SATISFIED
details_pk_unique: SATISFIED
details_order_fk: SATISFIED
details_product_fk: SATISFIED
employees_pk_unique: SATISFIED
employees_office_fk: SATISFIED
employees_manager_fk: SATISFIED
offices_pk_unique: SATISFIED
offices_volume: SATISFIED
```

Each line names an expectation and its outcome. The command exits `0` when every expectation is
satisfied, and exits `1` with `Dataset validation failed` if any expectation is violated.

**A meaningful quality check.** `orders_status_enum` checks that every `STATUS` value is one of the
values observed in the source. To see the check catch a real problem, corrupt a copy of the data and
validate it:

```bash
rm -rf out/bad && cp -r out/steelwheels out/bad
sed -i '2s/,Shipped,/,Bogus,/' out/bad/orders.csv
docker compose run --rm tdf validate --database steelwheels --data-dir /out/bad
rm -rf out/bad
```

Expected: `orders_status_enum: UNEXPECTED_VIOLATION ['Bogus']`, then `Error: Dataset validation failed`,
with a non-zero exit code. (`sed -i` is GNU syntax; on macOS use `sed -i ''`.)

## Step 13 — Inspect the Ontology

Open Neo4j Browser at <http://localhost:17474> and select the `test-data-factory` database. Each
query below is read-only. Run them one at a time.

**Database → Table → Column**

```cypher
MATCH p = (d:Database)-[:HAS_TABLE]->(t:Table)-[:HAS_COLUMN]->(c:Column)
WHERE d.name = 'steelwheels' AND t.name IN ['orders', 'customers']
RETURN p
LIMIT 60;
```

**Table → GeneratorContract → GenerationPolicy**

```cypher
MATCH p = (t:Table)-[:HAS_GENERATOR_CONTRACT]->(:GeneratorContract)-[:HAS_POLICY]->(:GenerationPolicy)
RETURN p;
```

**GenerationPolicy → ColumnGroup → Generator**

```cypher
MATCH p = (pol:GenerationPolicy {name: 'orders_functional'})-[:HAS_COLUMN_GROUP]->(:ColumnGroup)-[:USES_GENERATOR]->(:Generator)
RETURN p;
```

**GenerationPolicy → Expectation**

```cypher
MATCH p = (:GenerationPolicy)-[:ENFORCES]->(:Expectation)
RETURN p;
```

**DataProfile → ProfileSegment → ProfileObservation → ProfileMetric**

```cypher
MATCH p = (:DataProfile)-[:HAS_SEGMENT]->(:ProfileSegment)-[:HAS_OBSERVATION]->(:ProfileObservation)-[:USES_METRIC]->(:ProfileMetric)
WHERE EXISTS { MATCH (:ProfileObservation)-[:ABOUT]->(:Column {table: 'orders'}) }
RETURN p
LIMIT 40;
```

**Table → Table relationships**

```cypher
MATCH p = (parent:Table)-[:RELATES_TO]->(child:Table)
RETURN p;
```

Some labels and relationships in `docs/ONTOLOGY.md` are defined for later phases and are not written
by the current CLI (for example `GenerationRun`, `ValidationResult`, `DERIVED_FROM`). The queries
above only use types that the CLI writes.

Note: the policy label is `GeneratorContract` in the database. Some planning documents call it
`GenerationContract`.

## Step 14 — Clean Up

**Normal shutdown.** Stops and removes the containers and network, keeps the Neo4j data volume.
Your registered metadata, contracts and profiles survive:

```bash
docker compose down
```

**Destructive cleanup.** Removes the containers, network and the `tdf-neo4j-data` volume. All Neo4j
data for this project is deleted, and you must register and profile again:

```bash
docker compose down -v
```

Both commands only affect the Compose project `tdf` (the `name:` in `compose.yaml`). They do not
touch the devcontainer project or its volumes.

Generated CSV files in `./out` are on the host and are **not** removed by either command. Delete
them manually if you no longer need them:

```bash
rm -rf out/steelwheels
```

Do not run `docker system prune` as part of this tutorial. It affects unrelated Docker resources.

## Known limitations

- **No inspection CLI.** There is no `tdf` command to list databases, tables, columns, profiles,
  policies or expectations. Use Cypher (Step 13).
- **No authoring CLI.** Policies, column groups, generators and expectations are defined only in
  contract YAML, loaded with `tdf contract load`.
- **FUNCTIONAL intent only.** `PERFORMANCE` and `EDGE` policies are stored but not used by
  `generate` or `validate`. The CLI has no intent option.
- **CSV output only.** Generated data is written as CSV.
- **Validation results are not stored.** `validate` prints results. They are not written to Neo4j.
- **Offline generation is not supported for this contract.** `generate --contract ... --erd ...`
  without `--database` loads no profiles, so contracts that use `source: profile` (SteelWheels does)
  fail. Use `--database` as shown above.
- **Stubs.** `tdf repair` always fails ("not available in Phase 1"). `tdf report` prints a placeholder.
- **Expectation inference is not implemented.** Expectations are declared in the contract, not
  inferred from profiles.
- **Neo4j edition.** The Compose file uses Neo4j Enterprise, as the development environment does.
  Neo4j Enterprise requires accepting its license terms.
