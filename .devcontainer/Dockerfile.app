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

USER root

RUN apt-get update \
    && apt-get install --yes --no-install-recommends ca-certificates curl git \
    && pip install --no-cache-dir \
        "code-review-graph==${CODE_REVIEW_GRAPH_VERSION}" \
        "duckdb==1.5.6" \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p /home/developer/.config/opencode /home/developer/.local/share/opencode \
    && chown -R developer:developer /home/developer/.config /home/developer/.local

USER developer

RUN curl --fail --silent --show-error --location https://opencode.ai/install \
    | bash -s -- --version "${OPENCODE_VERSION}" --no-modify-path

ENV PATH="/home/developer/.opencode/bin:${PATH}"

FROM runtime AS production
