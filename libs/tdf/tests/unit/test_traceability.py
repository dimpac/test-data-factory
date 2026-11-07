"""Every Phase 1 requirement must be covered by at least one test marked with its ID."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

TESTS = Path(__file__).resolve().parents[1]

PHASE_1_ACS = {"AC-01", "AC-02", "AC-03", "AC-05", "AC-06", "AC-07", "AC-08", "AC-09"}
PHASE_1_FRS = {
    "FR-META-01", "FR-META-02", "FR-META-03", "FR-META-04", "FR-META-05", "FR-META-06",
    "FR-PROF-02", "FR-PROF-03", "FR-PROF-05", "FR-PROF-06",
    "FR-CON-01", "FR-CON-04", "FR-CON-05", "FR-CON-06", "FR-CON-09", "FR-CON-10",
    "FR-GEN-01", "FR-GEN-02", "FR-GEN-04", "FR-GEN-05", "FR-GEN-07", "FR-GEN-08",
    "FR-GEN-09", "FR-GEN-10", "FR-GEN-13", "FR-GEN-14",
    "FR-VAL-01", "FR-VAL-02", "FR-VAL-04",
    "FR-CLI-01", "FR-CLI-02",
}


def _ids_in(path: Path) -> set[str]:
    ids: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.Call) and getattr(node.func, "attr", "") == "req":
            ids.update(a.value for a in node.args if isinstance(a, ast.Constant))
    return ids


def _covered() -> set[str]:
    return set().union(*(_ids_in(p) for p in TESTS.rglob("test_*.py")))


@pytest.mark.parametrize("requirement", sorted(PHASE_1_ACS | PHASE_1_FRS))
def test_requirement_is_covered(requirement):
    assert requirement in _covered()


def test_withdrawn_ac_04_is_not_tested():
    assert "AC-04" not in _covered()
