# Operations

Procedures for the production-style stack (`compose.yaml`, Compose project `tdf`). The walkthrough is
in [`TUTORIAL.md`](../TUTORIAL.md).

## Start and stop
```bash
cp .env.changeme .env            # set NEO4J_PASSWORD
docker compose build tdf
docker compose up -d --wait neo4j   # waits for the Bolt health check
docker compose run --rm tdf --help
docker compose down              # keep data
docker compose down -v           # delete the Neo4j volume (metadata, contracts, profiles)
```
Do not use `docker system prune`; it affects unrelated resources.

## Configuration and secrets
| Variable | Purpose |
|---|---|
| `NEO4J_USERNAME`, `NEO4J_PASSWORD`, `NEO4J_DATABASE` | Credentials and database; read from `.env`, never baked into the image |
| `NEO4J_URL` | Set to `bolt://neo4j:7687` by Compose |
| `TDF_NEO4J_HTTP_PORT`, `TDF_NEO4J_BOLT_PORT` | Host ports (defaults 17474 and 17687, bound to 127.0.0.1) |

`NEO4J_PASSWORD` is applied only when the data volume is first created. To change it, restore the old
value or run `docker compose down -v`. `.env` is git-ignored.

Input and output: example inputs (ERD, DuckDB, contract) are bundled read-only under `/opt/tdf`. Output
goes to the `/out` volume, which Compose maps to `./out`. On Linux the container user is uid 1000, so
`./out` must be writable by it.

## Logs and diagnostics
- CLI: one `Error: ...` line on stderr and exit code 1 for known failures; `validate` prints one
  line per expectation (`SATISFIED`, `UNEXPECTED_VIOLATION`, ...). No separate log files exist.
- Neo4j: `docker compose logs neo4j`; health with `docker compose ps neo4j`.
- Graph inspection: read-only Cypher in Neo4j Browser (TUTORIAL step 13).

## Known failure modes
| Symptom | Cause and action |
|---|---|
| `NEO4J_PASSWORD is required` | `.env` missing or empty; set it |
| `Neo4j authentication failed` | Password differs from the one the volume was created with; see above |
| `Neo4j is unavailable` | Neo4j not healthy yet or `NEO4J_URL` wrong; run `docker compose up -d --wait neo4j` |
| `Database '...' is not registered` | Run `metadata register` first (data is lost if the volume was removed) |
| `Cannot write output to ...` | `./out` missing or not writable by uid 1000 |
| `requires a profile` | Offline `--contract` mode with profile-driven generators; use `--database` |
| Validation `UNEXPECTED_VIOLATION` | The dataset breaks an expectation; do not use it. Regenerate |

## Partial runs and recovery
Generation builds all tables in memory and writes CSVs only after every table succeeds, so a generation
error leaves no new output. A failure while writing files (for example a full disk) can leave some CSVs;
delete the output directory and rerun. Existing files in an output directory are overwritten but not
cleaned, so use a fresh directory. Registration is documented as idempotent (README); re-running was not separately tested in this
review. Each profile run is stored as a new `DataProfile`. Recovery from a lost graph is to re-run
`register`, `contract load` and `profile`.

## Local to cloud: CI/CD path (proposed, not provisioned)
1. **Pull request validation:** `scripts/verify.sh` (unit tests, CLI smoke, controlled failure).
2. **Unit and integration tests:** `scripts/verify.sh --integration` on a runner with Docker, using an
   isolated Compose project.
3. **Image build:** `docker build` of the root `Dockerfile`, tagged with the git SHA and version.
4. **Scanning:** dependency audit of `requirements.txt` and an image scan; fail on high severity.
5. **Versioned artifact:** tag releases (for example `v0.1.0`); the image is the artifact.
6. **Registry:** push to a private registry (ECR, GAR or ACR).
7. **Cloud execution:** run `tdf` as a short-lived container job (for example a scheduled or on-demand
   task) next to a managed Neo4j; the CLI is batch, so no long-running service is needed.
8. **Config and secrets:** environment-specific `NEO4J_*` values from the platform secret manager,
   injected as environment variables; never in the image or the repository.
9. **Monitoring:** job exit codes, container logs and Neo4j health; alert on non-zero exit. A run
   record in the graph does not exist yet (`tdf report` is a placeholder).
10. **Promotion and rollback:** promote the same image digest dev, test, prod after the integration
    suite passes; roll back by redeploying the previous digest. Neo4j metadata is not versioned by the
    image, so contracts are reloaded from the versioned YAML after a rollback.
