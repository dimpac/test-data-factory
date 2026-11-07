# Repository Guidance

This file is the authoritative guidance for agents working in this repository.

## Project Structure

- `apps/hello-world`: distributable hello-world application.
- `libs/utils`: shared utility library starter.
- `libs/tdf`: Test Data Factory package (CLI `tdf`), with unit and integration tests.
- `requirements.txt`: pinned Python dependencies installed in the development image.
- `.devcontainer`: application, Neo4j, Docker Compose, and VS Code devcontainer configuration.
- `opencode.json`: project OpenCode configuration, including the Code Review Graph MCP server.
- `docs/ONTOLOGY.md`: reference for the Test Data Factory graph ontology (node labels and relationships); diagram source in `docs/ontology.mmd`.
- `docs/PRD.md`: product requirements, acceptance criteria, roadmap, and open architectural decisions.

## Development Conventions

- Use Python 3.12 or newer for package development. The application container uses Python 3.14.
- Keep Python packages in a `src` layout and define package metadata in `pyproject.toml`.
- Prefer small, focused changes and add tests when behavior becomes non-trivial.
- Never commit `.env` or embed credentials in source, Compose files, or images.
- Use `.env.changeme` as the documented environment template.
- Keep the OpenCode version in `.devcontainer/Dockerfile.app` aligned with the host installation.
- Keep host OpenCode configuration and authentication mounts read-only and development-only.
- Keep Code Review Graph data under the ignored `.code-review-graph` directory.
- Do not resolve the open architectural decisions (AD-xxx) in `docs/PRD.md` without explicit approval.

## Common Commands

```bash
python -m pip install ./apps/hello-world
hello-world
python -m pip install ./libs/utils
python -m pip install -r requirements.txt && python -m pip install -e ./libs/tdf
pytest libs/tdf/tests -m "not neo4j"
pytest libs/tdf/tests
docker compose -f .devcontainer/docker-compose.yml build
docker compose -f .devcontainer/docker-compose.yml up
```

Neo4j development data is intentionally ephemeral. The Compose service mounts `/data` as
`tmpfs` so recreated containers initialize with the credentials currently stored in `.env`.
