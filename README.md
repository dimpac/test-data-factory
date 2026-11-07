# Test Data Factory

Python development scaffold with a containerized hello-world application and an ephemeral
Neo4j Enterprise development database.

## Local Packages

Install and run the application:

```bash
python -m pip install ./apps/hello-world
hello-world
```

Install the shared utility library:

```bash
python -m pip install ./libs/utils
```

## Containers

Create the local environment file and set a non-empty Neo4j password before starting Compose:

```bash
cp .env.changeme .env
docker compose -f .devcontainer/docker-compose.yml up --build
```

The graph publishes Neo4j Browser on `http://localhost:7474` and Bolt on
`bolt://localhost:7687`. Its `/data` directory uses `tmpfs`, so development data is discarded
when the container is removed.

The repository can also be opened directly in VS Code using its devcontainer configuration.
The development image includes OpenCode `1.19.3`, matching the host installation, and mounts
the host's `opencode.json` and `auth.json` read-only into the `developer` user's home directory.
It uses the `en_AU.UTF-8` locale and `Australia/Sydney` timezone, including daylight-saving
offsets in Git commit timestamps.

## SteelWheels Database

When the devcontainer is created, each CSV file directly under `data/` is imported into
`data/steelwheels.duckdb`. Table names are derived from CSV filename stems, and DuckDB infers
column names and types from each file. The generated database is ignored by Git.

Rebuild the database after changing the CSV files:

```bash
python .devcontainer/setup-steelwheels.py
```

Connect to it with the DuckDB CLI included in the development image:

```bash
duckdb data/steelwheels.duckdb
```

The app Dockerfile has separate targets for development tooling and a minimal production image:

```bash
docker build --target development -f .devcontainer/Dockerfile.app -t test-data-factory:dev .
docker build --target production -f .devcontainer/Dockerfile.app -t test-data-factory:prod .
```

## Code Review Graph

The development image includes Code Review Graph `2.3.9`. The devcontainer initializes the graph
when it is created, and the project `opencode.json` configures OpenCode to launch the MCP server
locally over stdio inside the app container. The server watches the workspace and incrementally
updates the graph while OpenCode is running. No separate CRG Compose service or network port is
required.

Check the integration from the app container with:

```bash
opencode mcp list
code-review-graph status
```
