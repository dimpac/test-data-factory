# Agentic workflow

Only facts recorded in the repository are stated here. Anything else is marked
**requires human input**.

## Tools and models
- **OpenCode** (version pinned in `.devcontainer/Dockerfile.app`) running in a non-root devcontainer;
  host OpenCode config is mounted read-only.
- **Code Review Graph** MCP server (`opencode.json`) for structural lookups.
- **Models used per phase: requires human input.** The task brief states that a "Haiku" model wrote
  the first version of `TUTORIAL.md`; the repository does not record model names or token use. No
  savings are claimed.

## Process (from `.instructions/`, `.plans/`, `.feedback/` and git history)
1. **Scaffold and isolate** (`d681c4e`..`cb7b7bc`): devcontainer, `AGENTS.md` as authoritative
   instructions. The agent switched a base image to Node; this was reverted (`8933b21`).
2. **Requirements first** (`218e535`, `4fb5678`): ontology, then PRD with acceptance criteria and open
   decisions. `AGENTS.md` forbids resolving AD-xxx without approval.
3. **Plan, then tests, then implementation**: `.plans/03_phase1_mvp.md` (planning only), failing tests
   (`5266813`), implementation (`0ea92e5`). Planning and implementation were separate instructions.
4. **Review with an approval gate** (`.feedback/04_phase1_mvp_implementation.md`): findings with
   evidence, then a stop for human approval. Fixes: `2c4afc8`, `4371646`.
5. **Packaging** (`8d67dc1`): production image and tutorial, from the packaging instruction file.
6. **Final compliance review** (the change that added this directory): assessed first, a plan was
   presented and approved by the human (including the CLI error-handling change, removal of the
   `production` stage in `Dockerfile.app`, keeping `libs/utils`, and no commit), then implemented.

All commits are authored by the human owner. The repository does not record which commits contain
agent-written code, or the chat history behind each instruction (**requires human input**).

## Delegation and verification
Delegation was by written instruction files with explicit scope, exclusions and acceptance criteria.
Agent output was verified by tests, by running the Docker workflow and by probe scripts. In the final
review, executing the real workflow found defects that the earlier tests had not (see `verify.md`:
Windows default-encoding failure, silent success for an unregistered database, tracebacks).

## Representative corrections
- Base image changed to Node, reverted (`8933b21`).
- Silent `zip()` truncation of generator output, replaced by a cardinality check (`2c4afc8`).
- Final review: the stale README statement that the production image contained only hello-world was
  corrected, and my own first attempt at a regression test was found to pass for the wrong reason
  (it failed earlier on a profile-dependent generator) and was rewritten.

## Limitations
Model choice, token use and prompt history are not recorded. The earlier README claim that every
commit was reviewed by a human cannot be proven from the repository beyond authorship, so it was
removed. The `.instructions/` (04-06) and `.feedback/` files are untracked, so their provenance is
only the local files.
