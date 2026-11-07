FROM node:24-slim AS opencode

ARG OPENCODE_VERSION=1.19.3

RUN npm install --global --allow-scripts=opencode-ai "opencode-ai@${OPENCODE_VERSION}" \
    && opencode --version


FROM python:3.14-slim AS runtime

RUN groupadd --gid 1000 developer \
    && useradd --uid 1000 --gid developer --create-home --shell /bin/bash developer

WORKDIR /opt/hello-world

COPY apps/hello-world/pyproject.toml ./pyproject.toml
COPY apps/hello-world/src ./src

RUN python -m pip install --no-cache-dir .

USER developer

CMD ["hello-world"]


FROM runtime AS development

USER root

RUN apt-get update \
    && apt-get install --yes --no-install-recommends ca-certificates git libstdc++6 ripgrep \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p /home/developer/.config/opencode /home/developer/.local/share/opencode \
    && chown -R developer:developer /home/developer/.config /home/developer/.local

COPY --from=opencode /usr/local/lib/node_modules/opencode-ai/bin/opencode.exe /usr/local/bin/opencode

USER developer


FROM runtime AS production
