#!/usr/bin/env bash
set -euo pipefail

# Editable install of the Test Data Factory CLI. pip installs console scripts for the
# non-root user into ~/.local/bin, which the image adds to PATH.
python -m pip install --user --no-warn-script-location --quiet -e ./libs/tdf
python .devcontainer/setup-steelwheels.py

if code-review-graph status --json >/dev/null 2>&1; then
    code-review-graph update --quiet
else
    code-review-graph build --quiet
fi
