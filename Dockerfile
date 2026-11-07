# syntax=docker/dockerfile:1

# Production image for the Test Data Factory `tdf` CLI.
# Build: docker compose build tdf
# Run:   docker compose run --rm tdf --help

ARG PYTHON_IMAGE=python:3.14-slim

FROM ${PYTHON_IMAGE} AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:${PATH}"

WORKDIR /build

# Pinned runtime versions. requirements.txt is used only as a constraints file so
# that test-only packages (pytest) are not installed into the runtime image.
COPY requirements.txt ./
COPY libs/tdf ./libs/tdf
RUN python -m pip install --upgrade pip \
 && python -m pip install -c requirements.txt ./libs/tdf

# Build the SteelWheels DuckDB from the committed CSV files.
COPY data ./data
COPY .devcontainer/setup-steelwheels.py ./.devcontainer/setup-steelwheels.py
RUN python .devcontainer/setup-steelwheels.py \
      --data-dir data \
      --database /build/steelwheels.duckdb


FROM ${PYTHON_IMAGE} AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:${PATH}"

RUN groupadd --gid 1000 tdf \
 && useradd --uid 1000 --gid 1000 --home-dir /home/tdf --create-home --shell /usr/sbin/nologin tdf

COPY --from=builder /opt/venv /opt/venv

# Bundled SteelWheels example assets, owned by root and read-only to the tdf user.
# Paths mirror the repository layout so repository-relative references in the
# contract (for example data/allCountriesCSV.csv.gz) resolve from WORKDIR.
WORKDIR /opt/tdf
COPY --from=builder /build/steelwheels.duckdb ./data/steelwheels.duckdb
COPY data/allCountriesCSV.csv.gz ./data/allCountriesCSV.csv.gz
COPY docs/steelwheels_erd.mmd ./docs/steelwheels_erd.mmd
COPY libs/tdf/config/steelwheels/contract.yaml ./config/steelwheels/contract.yaml

# Writable output location; mount a host directory here to keep generated data.
RUN mkdir -p /out && chown tdf:tdf /out
VOLUME ["/out"]

USER tdf

ENTRYPOINT ["tdf"]
CMD ["--help"]
