import csv
from datetime import date, datetime

import pytest

from tdf.output import write_csv

pytestmark = pytest.mark.req("FR-GEN-13", "FR-GEN-14")

ROWS = [{"A": i, "B": f"v{i}"} for i in range(25)]


def test_header_and_column_order(tmp_path):
    path = tmp_path / "t.csv"
    assert write_csv(path, ["B", "A"], iter(ROWS)) == 25
    with open(path, newline="", encoding="utf-8") as handle:
        rows = list(csv.reader(handle))
    assert rows[0] == ["B", "A"]
    assert rows[1] == ["v0", "0"]
    assert len(rows) == 26


def test_batched_write_equals_single_write(tmp_path):
    one, many = tmp_path / "one.csv", tmp_path / "many.csv"
    write_csv(one, ["A", "B"], iter(ROWS), batch_size=10_000)
    write_csv(many, ["A", "B"], iter(ROWS), batch_size=7)
    assert one.read_bytes() == many.read_bytes()


def test_accepts_a_one_shot_iterator(tmp_path):
    consumed = []

    def gen():
        for row in ROWS:
            consumed.append(row["A"])
            yield row

    assert write_csv(tmp_path / "t.csv", ["A", "B"], gen(), batch_size=5) == 25
    assert len(consumed) == 25


def test_nulls_and_temporal_values(tmp_path):
    path = tmp_path / "t.csv"
    write_csv(path, ["D", "T", "N"], [{"D": date(2020, 1, 2), "T": datetime(2020, 1, 2, 3, 4, 5), "N": None}])
    with open(path, newline="", encoding="utf-8") as handle:
        _, row = list(csv.reader(handle))
    assert row == ["2020-01-02", "2020-01-02T03:04:05", ""]


def test_non_ascii_values_are_written_as_utf8(tmp_path):
    path = tmp_path / "t.csv"
    write_csv(path, ["A"], iter([{"A": "Bac\u0103u"}]))
    assert path.read_bytes().decode("utf-8").splitlines()[1] == "Bac\u0103u"
