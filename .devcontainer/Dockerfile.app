FROM python:3.14-slim AS runtime

COPY apps/hello-world /tmp/hello-world

RUN pip install --no-cache-dir /tmp/hello-world \
    && rm -rf /tmp/hello-world \
    && groupadd --gid 1000 developer \
    && useradd --uid 1000 --gid developer --create-home --shell /bin/bash developer

USER developer

CMD ["hello-world"]

FROM runtime AS development

ARG OPENCODE_VERSION=1.19.3
ARG CODE_REVIEW_GRAPH_VERSION=2.3.9
# DUCKDB_VERSION must match the duckdb pin in requirements.txt.
ARG DUCKDB_VERSION=1.5.6

USER root

COPY requirements.txt /tmp/requirements.txt

RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install --yes --no-install-recommends \
        ca-certificates curl git locales tzdata \
    && localedef --inputfile=en_AU --charmap=UTF-8 en_AU.UTF-8 \
    && ln --symbolic --force /usr/share/zoneinfo/Australia/Sydney /etc/localtime \
    && printf '%s\n' 'Australia/Sydney' > /etc/timezone \
    && pip install --no-cache-dir \
        "code-review-graph==${CODE_REVIEW_GRAPH_VERSION}" \
        --requirement /tmp/requirements.txt \
    && curl --fail --silent --show-error --location \
        "https://github.com/duckdb/duckdb/releases/download/v${DUCKDB_VERSION}/duckdb_cli-linux-amd64.zip" \
        --output /tmp/duckdb-cli.zip \
    && python -m zipfile --extract /tmp/duckdb-cli.zip /tmp/duckdb-cli \
    && install --mode=0755 /tmp/duckdb-cli/duckdb /usr/local/bin/duckdb \
    && duckdb --version >/dev/null \
    && rm -rf /tmp/duckdb-cli /tmp/duckdb-cli.zip /tmp/requirements.txt \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p /home/developer/.config/opencode /home/developer/.local/share/opencode \
    && chown -R developer:developer /home/developer/.config /home/developer/.local

ENV LANG=en_AU.UTF-8 \
    LANGUAGE=en_AU:en \
    LC_ALL=en_AU.UTF-8 \
    TZ=Australia/Sydney

USER developer

RUN curl --fail --silent --show-error --location https://opencode.ai/install \
    | bash -s -- --version "${OPENCODE_VERSION}" --no-modify-path

ENV PATH="/home/developer/.opencode/bin:/home/developer/.local/bin:${PATH}"

FROM runtime AS production
