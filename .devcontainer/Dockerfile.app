FROM python:3.14-slim

RUN groupadd --gid 1000 developer \
    && useradd --uid 1000 --gid developer --create-home --shell /bin/bash developer

WORKDIR /opt/hello-world

COPY apps/hello-world/pyproject.toml ./pyproject.toml
COPY apps/hello-world/src ./src

RUN python -m pip install --no-cache-dir .

USER developer

CMD ["hello-world"]
