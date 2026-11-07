# Verification

Environment: Windows 11 host with Git Bash, Docker 26.1.4, Compose v2.27, host Python 3.12.6,
production image on Python 3.14. Results below are from runs made during the final review.

## Commands
```bash
scripts/verify.sh                 # fast: unit tests, CLI smoke, controlled failure
scripts/verify.sh --integration   # + image build, SteelWheels workflow, corruption check, Neo4j tests
```
Both exit non-zero when a mandatory check fails.

## Verified results
| Check | Result |
|---|---|
| Unit tests (`-m "not neo4j"`) | 189 passed, 21 deselected |
| Neo4j-backed tests (`-m neo4j`, isolated project `tdf-verify`) | 21 passed |
| `scripts/verify.sh --integration` | exit 0, "All checks passed" |
| Production image build (`docker compose build tdf`) | success; user `tdf`, entrypoint `tdf`, no `NEO4J_*` in image env |
| Image contents | `/opt/tdf` holds only config, data and docs; no pytest or agent tools; uid 1000 |
| Workflow in the production image | register, contract load (6), profile (6 tables), generate (3597 rows), validate (15 SATISFIED, exit 0) |
| Reproducibility | same seed gives identical CSVs (`diff -r`); `--rows orders=50 --rows orderdetails=50` gives 366 rows |
| Cleanup | `docker compose down -v` leaves no `tdf*` volume; `out/` is git-ignored |

## Controlled failures (all verified)
| Scenario | Outcome |
|---|---|
| Unknown generator in a contract (`verify.sh`, and unit test) | `Error: Unsupported generator nosuchgen`, exit 1, no output directory |
| Corrupted `orders.csv` (`STATUS` set to `Bogus`) | `orders_status_enum: UNEXPECTED_VIOLATION ['Bogus']`, exit 1 |
| Foreign key set to a missing customer (`verify.sh --integration`) | `orders_customer_fk: UNEXPECTED_VIOLATION`, exit 1 |
| Missing `NEO4J_PASSWORD` | `Error: NEO4J_PASSWORD is required; ...`, exit 1 |
| Wrong Neo4j password | `Error: Neo4j authentication failed; ...`, exit 1 |
| Unreachable Neo4j (unit test) | `Error: Neo4j is unavailable; ...`, exit 1 |
| Unregistered database name (unit test) | `Error: Database 'x' is not registered; ...`, exit 1 |
| Unwritable output path (unit test) | `Error: Cannot write output to ...`, exit 1 |

## Defects found and fixed in this review
1. **Tracebacks for known errors** (contract, generator, configuration, Neo4j): now one-line errors.
2. **Windows default encoding**: CSVs were written and read with the host encoding, so non-ASCII
   postal names (for example `Bac\u0103u`) failed `generate` with a `charmap` error when the CLI ran
   on a Windows host. CSV I/O is now UTF-8; regression test `test_non_ascii_values_are_written_as_utf8`.
   The Linux container was not affected.
3. **Silent success for an unregistered database**: `generate` and `validate` on a database with no
   stored schema exited 0 (for example `validate --database nosuchdb` printed nothing). They now fail.
   `validate` also fails when there are no expectations to evaluate.

## Known gaps (not fixed, by design)
- Devcontainer: the `development` target of `.devcontainer/Dockerfile.app` builds, and in it the editable
  install of `tdf` works and `hello-world` is absent. The full `post-create.sh` (DuckDB rebuild, Code
  Review Graph) and VS Code "Reopen in Container" were **not** run.
- Stale files in an existing `--out` directory are not removed before generating.
- Unexpected (non-domain) exceptions still show a traceback.
- Tests were run on a Windows host and in Linux containers (Neo4j); no macOS or ARM run.
- No vulnerability scan, lint or type check has been run.

## Proposed CI checks (not executed)
Per pull request: `scripts/verify.sh`. On main or release: `scripts/verify.sh --integration`, image
build, dependency and image vulnerability scan (for example `pip-audit` and Trivy), then publish.
