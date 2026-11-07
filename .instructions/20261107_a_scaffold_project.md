# Scaffold Test Data Factory

Scaffold the Test Data Factory repository as a Python development project with a VS Code devcontainer, a containerised hello-world application and a Neo4j development database

## Repository Instructions

Create `AGENTS.md` as the authoritative repository guidance

Create `CLAUDE.md` that tells Claude to read and follow `AGENTS.md` as the authoritative source

Create `.claude/skills/00-hello-world/SKILL.md` with valid skill frontmatter

Create `.gitattributes` with a repository-wide `* text=auto eol=lf` rule so tracked text files
use LF in both the Git index and working tree. Ensure all initial text files are written with LF
line endings to prevent mixed-EOL warnings when Git normalizes files.

## Hello-World Application

Create a distributable Python application under `apps/hello-world`

Create a starter utils library under `libs/utils`

## Environment Template

Create `.env.changeme` with these variables:

```dotenv
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=
NEO4J_DATABASE=test_data_factory
NEO4J_URL=bolt://localhost:7687
```

Ensure `.env` is ignored by Git

## Container Images

Create `.devcontainer/Dockerfile.app` based on `python:3.14-slim`.

The application image must:

- Copy and install `apps/hello-world` as a Python package during the image build
- Create a non-root `developer` user and group with UID and GID 1000
- Run as `developer` and make `hello-world` the default command

The development image must:

- Install the Debian `locales` and `tzdata` packages non-interactively
- Generate and use the `en_AU.UTF-8` locale
- Use the `Australia/Sydney` timezone, including its daylight-saving offset
- Set `LANG=en_AU.UTF-8`, `LANGUAGE=en_AU:en`, `LC_ALL=en_AU.UTF-8`, and
  `TZ=Australia/Sydney` so shell commands and Git commits use the expected locale and timezone

Create `.devcontainer/Dockerfile.graph` based on `neo4j:5-enterprise`.


## Docker Compose

Create `.devcontainer/docker-compose.yml` with `test-data-factory-app` and `test-data-factory-graph` services.

The `test-data-factory-app` service must:

- Build from `.devcontainer/Dockerfile.app` with the repository root as its build context.
- Use `linux/amd64`.
- Run indefinitely as the `developer` user for devcontainer use.
- Bind-mount the repository at `/workspaces/test-data-factory` with cached consistency.
- Use that mounted directory as its working directory.

The `graph` service must:

- Build from `.devcontainer/Dockerfile.graph` with the repository root as its build context.
- Publish HTTP port 7474 and Bolt port 7687 to the same host ports.
- Load the root `.env` file.
- Accept the Neo4j Enterprise license through `NEO4J_ACCEPT_LICENSE_AGREEMENT=yes`.
- Construct Neo4j's supported `NEO4J_AUTH` value from `NEO4J_USERNAME` and `NEO4J_PASSWORD` before invoking the image's standard `/startup/docker-entrypoint.sh neo4j` command. Escape Compose interpolation where necessary so expansion occurs inside the container.
- Remove the individual credential and application variables from the Neo4j process environment after constructing `NEO4J_AUTH`.
- Mount `/data` as `tmpfs`. This is required: the Neo4j image otherwise creates an anonymous data volume that can survive container recreation, causing `NEO4J_AUTH` to be ignored because it only sets the password before the database is initialized. Development graph data is intentionally ephemeral so a rebuilt container always initializes with the current `.env` credentials.

Do not embed a password in the Compose file or Docker image.

## Devcontainer

Create `.devcontainer/devcontainer.json` that:

- Uses `.devcontainer/docker-compose.yml` and the `test-data-factory-app` service.
- Opens the repository at `/workspaces/${localWorkspaceFolderBasename}`.
- Keeps the development service running with its Compose command.
- Installs the VS Code Python, debugpy, and Mermaid preview extensions.
- Runs `.devcontainer/post-create.sh` after creation.

Create an executable `.devcontainer/post-create.sh` with a valid Bash shebang and a simple successful post-create action.
