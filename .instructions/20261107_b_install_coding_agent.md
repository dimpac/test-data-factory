# Install Coding Agent

Bake Opencode AI (https://opencode.ai/) in .devcontainer/Dockerfile.app

Use the same version in the container as in the host

Leverage opencode.json from .config/opencode
Leverage auth.json from  in .local/share/opencode/auth.json

Mounts are read only

Make sure .devcontainer/Dockerfile.app caters for two scenarios: development image and production image