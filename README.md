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
