# Plan: Phase 1 MVP - Implementation and Data Generation

Source instructions: `.instructions/20261107_04_phase1_mvp_impl.md`
Related: `.plans/03_phase1_mvp.md` (tests), `docs/PRD.md`, `docs/ONTOLOGY.md`, `docs/steelwheels_erd.mmd`, `libs/tdf/config/steelwheels/contract.yaml`

Goal: implement the `tdf` package so the Phase 1 unit and integration tests pass, then generate a relationally consistent SteelWheels dataset from stored metadata and contracts.

Status: 170 tests pass (`libs/tdf/tests`). Docker was not available in the working environment, so the Compose changes are not verified by a container rebuild.

## 1. Decisions

### 1.1 Implementation

- All behaviour-bearing stubs in `libs/tdf/src/tdf` were implemented: ERD parser, DuckDB introspection, schema check, dependency ordering, contract loader and validation, profiling, generator registry, engine, CSV writer, independent validator, Neo4j client and repository, and the CLI.
- `tdf.validation` must not import generators or the engine. This is enforced by a unit test.
- Repeated runs are idempotent: metadata registration and contract loading use `MERGE`. Reloading a contract removes column groups that were dropped from the file.

### 1.2 Neo4j and environment

- Neo4j 5 rejects underscores in database names. `NEO4J_DATABASE` is now `test-data-factory` in `.env` and `.env.changeme`. The integration test database is `tdf-test`.
- `.env` must point `NEO4J_URL` to `bolt://test-data-factory-graph:7687` from inside the app container. `localhost` is only correct from the host.
- `docker-compose.yml`:
  - the app service loads `../.env` through `env_file` and sets `NEO4J_URL`;
  - the graph service sets `NEO4J_initial_dbms_default__database` from `NEO4J_DATABASE`, so the default database name is valid on startup.
- `.env` and credentials are never printed or committed. `NEO4J_PASSWORD` is required by `GraphClient.from_env`.
- Neo4j databases are created empty. Metadata has to be registered explicitly; creating the database does not register anything.

### 1.3 CLI and helper script

- `tdf` is installed to `~/.local/bin`, which is not on PATH in the default shell.
- `scripts/tdf-metadata-register <database> <erd> <source>` wraps `tdf metadata register`. It:
  - checks the argument count and that the ERD and DuckDB files exist;
  - loads `.env` when `NEO4J_PASSWORD` is unset;
  - falls back to `~/.local/bin/tdf` when `tdf` is not on PATH.
- Required workflow order for a dataset:
  1. `tdf metadata register` (or the script)
  2. `tdf contract load libs/tdf/config/steelwheels/contract.yaml`
  3. `tdf profile` for each table

  Profiling must run after the contract is loaded, because the contract declares the tuple sets and value-set columns that profiling emits. Profiling before loading fails with `profile has no tuple value set for [...]`.
- The graph copy of a contract can drift from the YAML file. `tdf contract load` must be re-run after any YAML change. No drift check is implemented yet.

### 1.4 Row counts

- `row_count` lives on each FUNCTIONAL `GenerationPolicy` in the YAML and is copied to Neo4j as a property on the `GenerationPolicy` node. `tdf generate` reads it from the graph; `--rows TABLE=COUNT` overrides it.
- `docs/ONTOLOGY.md` does not list `row_count` on `GenerationPolicy`. Documenting it is pending.
- The YAML is the authored source and is still required. It cannot be regenerated from the graph.

### 1.5 Profiling and value sets

- `AD-005` (cap of 100 distinct values for value sets) is unchanged and still provisional.
- Opt-in: a column group with `params: {value_set: true}` gets its full value list in the profile, even above the cap. This was chosen instead of raising the global cap, which would have resolved a provisional decision.
- Tuple sets are declared by the contract: every `tuple` column group gives a profile observation with that exact column list. The CLI reads them from the stored contract; the earlier hardcoded `CITY, STATE, COUNTRY` tuple was removed.

### 1.6 Generation

- Seeds are derived per table and column group from `sha256(seed:table:group)`, so groups do not share a random stream and output is reproducible.
- Foreign keys draw only from already generated parent rows. Nullable self-references point to earlier rows; the first row is null.
- The `tuple` generator supports `unique: true`, which samples without replacement and fails if the profile has fewer combinations than rows.
- The `faker` generator takes one provider per group (for example `phone_number`, `street_address`, `last_name`, `company`, `email`) and seeds Faker from the group seed.
- The `geo` generator reads `data/allCountriesCSV.csv` (columns `COUNTRY`, `POSTAL_CODE`, `CITY`, `SHORT_STATE`). It keeps one zip row's city, state, postal code and country together. The pool is cached per file and country set; the first read takes about 12 seconds.
- `TERRITORY` is derived from the chosen country by a lookup in the registry.

### 1.7 Contracts and data sources

- Offices and customers use `geo` for location. Employees, customers and offices use `faker` for person and contact fields (names, phone, address lines, employee email).
- The customers `customers_location_valid` expectation was removed. It checked against the seven source locations, which the geo generator is designed to exceed.
- Each column may have only one owner in a policy. Overlaps fail `validate_contract` (AD-008). POSTALCODE was moved from the customer text group to the location group for this reason.

## 2. Data quality findings

- **Source mojibake**: `Bacău` is stored double-encoded in `allCountriesCSV.csv` (`Bac─âu`), so generated rows carry the same text. The source was not modified.
- **Empty states**: Singapore and some other countries have no state. `STATE` is empty for them, which matches the source.
- **Territory for countries outside the source**: the source offices confirm AU=APAC, FR/UK=EMEA, JP=Japan, US=NA. Other territories (for example Canada=NA, Germany=EMEA) are an assumed regional grouping, not from the data.
- **Location consistency**: CITY, STATE, POSTALCODE and COUNTRY come from one zip row, so they are consistent with each other. The source offices' CITY/STATE/COUNTRY combinations (for example Tokyo with USA) are no longer used.
- **Country coverage**: the CSV covers all 25 mapped SteelWheels countries. Hong Kong and Israel are not in the file and are not sampled.

## 3. Current generated fields

| Table | Field group | Generator |
|---|---|---|
| customers | CUSTOMERNAME | faker `company` |
| customers | CONTACTLASTNAME, CONTACTFIRSTNAME | faker `last_name`, `first_name` |
| customers | PHONE, ADDRESSLINE1, ADDRESSLINE2 | faker `phone_number`, `street_address`, `secondary_address` |
| customers | CITY, STATE, POSTALCODE, COUNTRY | geo (postal CSV) |
| customers | CREDITLIMIT, SALESREPEMPLOYEENUMBER, CUSTOMERNUMBER | integer, foreign_key, sequence |
| offices | PHONE, ADDRESSLINE1, ADDRESSLINE2 | faker |
| offices | CITY, STATE, POSTALCODE, COUNTRY, TERRITORY | geo (TERRITORY derived from country) |
| employees | LASTNAME, FIRSTNAME, EMAIL | faker `last_name`, `first_name`, `email` |
| employees | EXTENSION, JOBTITLE | string (random) |
| employees | OFFICECODE, REPORTSTO, EMPLOYEENUMBER | foreign_key, sequence |
| orders, orderdetails, products | unchanged from the source-driven contract | categorical, timestamp, integer, sequence, foreign_key |

## 4. Open items

1. **Employee email is not derived from the name.** `swilliams@example.net` may be issued to `Anthony Nguyen`. A `first.last@domain` rule needs approval.
2. **Employee EXTENSION and JOBTITLE are random strings.** The source values are structured (`x5800`, `VP Sales`), so a Faker provider would not match them. A structured generator or a value list is needed.
3. **Territory for countries outside the source** needs confirmation.
4. **Mojibake in the postal source** needs a decision: fix at source, or normalise during load.
5. **Contract drift check**: warn or fail when the YAML hash differs from the stored contract.
6. **Docker verification**: the Compose changes (`env_file`, `NEO4J_URL`, database naming) have not been tested by rebuilding the container.
7. **`tdf report` is a placeholder**; `tdf repair` is an intentional Phase 1 stub.
8. **Documentation**: `row_count` on `GenerationPolicy` and the `geo` / `faker` generator parameters are not yet in `docs/ONTOLOGY.md` or `docs/PRD.md`.
9. **Test runtime**: the full suite takes about one minute because the location and Neo4j tests each read the 111 MB postal CSV.
10. **Open architectural decisions** AD-010 to AD-013 in `docs/PRD.md` are unresolved and must not be resolved without approval.

## 5. Verification

- Unit and integration suite: `set -a; source .env; set +a; python -m pytest libs/tdf/tests` (170 passed).
- Generation: `tdf generate --database steelwheels --seed 42 --out /tmp/tdf-out` (3,597 rows).
- Validation: `tdf validate --database steelwheels --data-dir /tmp/tdf-out` (15 expectations, all SATISFIED).
- Whitespace: `git diff --check`.
