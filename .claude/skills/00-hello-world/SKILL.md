---
name: 00-hello-world
description: Build, run, and troubleshoot the repository's hello-world Python application.
---

# Hello World

The application distribution is in `apps/hello-world` and exposes both of these entry points:

```bash
hello-world
python -m hello_world
```

Install it locally with `python -m pip install ./apps/hello-world`, or build and run it through
the `test-data-factory-app` service in `.devcontainer/docker-compose.yml`.
