#!/usr/bin/env bash
# Single verification entry point.
#   scripts/verify.sh                 fast checks (suitable for every PR; no Docker)
#   scripts/verify.sh --integration   fast checks + Docker build + SteelWheels workflow in an
#                                     isolated Compose project (tdf-verify) + Neo4j tests
# Exits non-zero as soon as a mandatory check fails.
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."
PYTHON="${PYTHON:-python}"
INTEGRATION=0
case "${1:-}" in
    "") ;;
    --integration) INTEGRATION=1 ;;
    *) echo "usage: $0 [--integration]" >&2; exit 2 ;;
esac

step() { printf '\n==> %s\n' "$*"; }
fail() { echo "FAIL: $*" >&2; exit 1; }

step "Unit tests (no services)"
"$PYTHON" -m pytest libs/tdf/tests -m "not neo4j" -q -p no:cacheprovider

step "CLI smoke test"
tdf --help >/dev/null || fail "tdf --help failed"

step "Controlled failure: invalid contract must be rejected"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
sed '0,/generator: sequence/s//generator: nosuchgen/' libs/tdf/config/steelwheels/contract.yaml > "$tmp/bad.yaml"
if tdf generate --contract "$tmp/bad.yaml" --erd docs/steelwheels_erd.mmd --out "$tmp/out" >"$tmp/log" 2>&1; then
    fail "invalid contract was accepted"
fi
grep -q "Unsupported generator nosuchgen" "$tmp/log" || fail "diagnostic missing: $(cat "$tmp/log")"
grep -q Traceback "$tmp/log" && fail "traceback leaked to the user"
[[ ! -e "$tmp/out" ]] || fail "output written despite failed generation"
echo "rejected as expected: $(grep Error "$tmp/log")"

if [[ $INTEGRATION -eq 0 ]]; then
    echo; echo "Fast checks passed. Run with --integration for the Docker workflow."
    exit 0
fi

step "Integration: build image and run SteelWheels workflow (Compose project tdf-verify)"
[[ -f .env ]] || fail ".env missing; copy .env.changeme and set NEO4J_PASSWORD"
set -a; . ./.env; set +a
[[ -n "${NEO4J_PASSWORD:-}" ]] || fail "NEO4J_PASSWORD is empty in .env"
export TDF_NEO4J_HTTP_PORT="${TDF_VERIFY_HTTP_PORT:-27474}" TDF_NEO4J_BOLT_PORT="${TDF_VERIFY_BOLT_PORT:-27687}"
# MSYS_NO_PATHCONV: Git Bash on Windows must not rewrite container paths such as /out.
dc() { MSYS_NO_PATHCONV=1 docker compose -p tdf-verify "$@"; }
cleanup() { dc down -v >/dev/null 2>&1 || true; rm -rf "$tmp"; }
trap cleanup EXIT
dc down -v >/dev/null 2>&1 || true   # only the tdf-verify project

mkdir -p out/verify
rm -rf out/verify/*
dc build tdf
dc up -d --wait neo4j
tdfrun() { dc run --rm tdf "$@"; }

tdfrun metadata register --database steelwheels --erd docs/steelwheels_erd.mmd --source data/steelwheels.duckdb
tdfrun contract load config/steelwheels/contract.yaml
for t in offices employees customers products orders orderdetails; do
    tdfrun profile --database steelwheels --source data/steelwheels.duckdb --table "$t"
done
tdfrun generate --database steelwheels --seed 42 --out /out/verify/good
tdfrun validate --database steelwheels --data-dir /out/verify/good | tee "$tmp/validate.txt"
[[ "$(grep -c ': SATISFIED' "$tmp/validate.txt")" -eq 15 ]] || fail "expected 15 SATISFIED expectations"
[[ -s out/verify/good/orders.csv ]] || fail "orders.csv missing or empty"

step "Integration: validation must reject corrupted output"
cp -r out/verify/good out/verify/bad
"$PYTHON" - <<'PY'
import csv, pathlib
p = pathlib.Path("out/verify/bad/orders.csv")
rows = list(csv.reader(p.open(newline="")))
i = rows[0].index("CUSTOMERNUMBER")
rows[1][i] = "99999999"
csv.writer(p.open("w", newline="")).writerows(rows)
PY
if tdfrun validate --database steelwheels --data-dir /out/verify/bad >"$tmp/bad.txt" 2>&1; then
    fail "corrupted dataset passed validation"
fi
grep -q "orders_customer_fk: UNEXPECTED_VIOLATION" "$tmp/bad.txt" || fail "FK violation not reported: $(cat "$tmp/bad.txt")"
echo "corruption rejected as expected"

step "Integration: Neo4j-backed tests (host Python, published port)"
NEO4J_URL="bolt://127.0.0.1:${TDF_NEO4J_BOLT_PORT}" "$PYTHON" -m pytest libs/tdf/tests -m neo4j -q -p no:cacheprovider
rm -rf out/verify

echo; echo "All checks passed (fast + integration)."
