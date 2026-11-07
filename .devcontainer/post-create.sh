#!/usr/bin/env bash
set -euo pipefail

hello-world
python .devcontainer/setup-steelwheels.py

if code-review-graph status --json >/dev/null 2>&1; then
    code-review-graph update --quiet
else
    code-review-graph build --quiet
fi
