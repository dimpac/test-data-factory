import pytest
from click.testing import CliRunner

from tdf.cli import main

pytestmark = pytest.mark.req("FR-CLI-01", "FR-CLI-02")

COMMANDS = ["metadata", "profile", "contract", "generate", "validate", "repair", "report"]


def test_help_lists_every_command():
    result = CliRunner().invoke(main, ["--help"])
    assert result.exit_code == 0
    for command in COMMANDS:
        assert command in result.output


@pytest.mark.parametrize("command", COMMANDS)
def test_each_command_has_help(command):
    result = CliRunner().invoke(main, [command, "--help"])
    assert result.exit_code == 0
    assert "Usage" in result.output


def test_generate_with_missing_contract_fails_with_actionable_message(tmp_path):
    result = CliRunner().invoke(main, ["generate", "--contract", str(tmp_path / "missing.yaml"), "--out", str(tmp_path)])
    assert result.exit_code != 0
    assert "missing.yaml" in result.output
    assert "No such command" not in result.output


def test_validate_with_missing_directory_fails_with_actionable_message(tmp_path):
    result = CliRunner().invoke(main, ["validate", "--database", "steelwheels", "--data-dir", str(tmp_path / "nope")])
    assert result.exit_code != 0
    assert "nope" in result.output
    assert "No such command" not in result.output


def test_repair_is_not_available_in_phase_1():
    result = CliRunner().invoke(main, ["repair"])
    assert result.exit_code != 0
    assert "No such command" not in result.output
    assert "phase" in result.output.lower()


def _bad_generator_contract(tmp_path):
    from tests.conftest import STEELWHEELS_CONTRACT

    path = tmp_path / "bad.yaml"
    path.write_text(STEELWHEELS_CONTRACT.read_text().replace("generator: sequence", "generator: nosuchgen", 1))
    return path


def test_unknown_generator_fails_cleanly_and_writes_nothing(tmp_path):
    from tests.conftest import STEELWHEELS_ERD

    out = tmp_path / "out"
    result = CliRunner().invoke(
        main, ["generate", "--contract", str(_bad_generator_contract(tmp_path)), "--erd", str(STEELWHEELS_ERD), "--out", str(out)]
    )
    assert result.exit_code == 1
    assert "Error: Unsupported generator nosuchgen" in result.output
    assert "Traceback" not in result.output
    assert not out.exists()


def test_missing_neo4j_password_fails_cleanly(monkeypatch, tmp_path):
    monkeypatch.delenv("NEO4J_PASSWORD", raising=False)
    result = CliRunner().invoke(main, ["validate", "--database", "steelwheels", "--data-dir", str(tmp_path)])
    assert result.exit_code == 1
    assert "NEO4J_PASSWORD is required" in result.output
    assert "Traceback" not in result.output


def test_unreachable_neo4j_fails_cleanly(monkeypatch, tmp_path):
    monkeypatch.setenv("NEO4J_PASSWORD", "x")
    monkeypatch.setenv("NEO4J_URL", "bolt://127.0.0.1:1")
    result = CliRunner().invoke(main, ["validate", "--database", "steelwheels", "--data-dir", str(tmp_path)])
    assert result.exit_code == 1
    assert "Neo4j is unavailable" in result.output
    assert "Traceback" not in result.output


def test_profile_dependent_contract_offline_fails_cleanly(tmp_path):
    from tests.conftest import STEELWHEELS_CONTRACT, STEELWHEELS_ERD

    result = CliRunner().invoke(
        main, ["generate", "--contract", str(STEELWHEELS_CONTRACT), "--erd", str(STEELWHEELS_ERD), "--out", str(tmp_path / "o")]
    )
    assert result.exit_code == 1
    assert "requires a profile" in result.output
    assert "Traceback" not in result.output
    assert not (tmp_path / "o").exists()


def test_unwritable_output_directory_fails_cleanly(tmp_path, small_erd):
    erd = tmp_path / "erd.mmd"
    erd.write_text(small_erd)
    contract = tmp_path / "c.yaml"
    contract.write_text(
        """database: t
contracts:
  - name: c
    table: customers
    version: 1
    policies:
      - name: p
        intent: FUNCTIONAL
        row_count: 2
        column_groups:
          - {name: key, columns: [CUSTOMERNUMBER], generator: sequence}
          - {name: n, columns: [CUSTOMERNAME], generator: string}
          - {name: l, columns: [CITY], generator: string}
          - {name: s, columns: [STATE], generator: string}
          - {name: c, columns: [COUNTRY], generator: string}
"""
    )
    blocker = tmp_path / "file"
    blocker.write_text("x")
    result = CliRunner().invoke(
        main, ["generate", "--contract", str(contract), "--erd", str(erd), "--out", str(blocker / "sub")]
    )
    assert result.exit_code == 1, result.output
    assert "Cannot write output" in result.output
    assert "Traceback" not in result.output


class _EmptyRepository:
    def __init__(self, graph):
        pass

    def get_schema(self, database):
        from tdf.metadata.models import SchemaModel

        return SchemaModel(tables={}, relationships=[])


@pytest.mark.parametrize("command", ["generate", "validate"])
def test_unregistered_database_is_an_error_not_a_success(monkeypatch, tmp_path, command):
    import tdf.cli as cli

    class _Graph:
        def close(self):
            pass

    monkeypatch.setattr(cli.GraphClient, "from_env", classmethod(lambda cls, database=None: _Graph()))
    monkeypatch.setattr(cli, "MetadataRepository", _EmptyRepository)
    args = ["--database", "ghost"] + (["--data-dir", str(tmp_path)] if command == "validate" else ["--out", str(tmp_path / "o")])
    result = CliRunner().invoke(main, [command, *args])
    assert result.exit_code == 1
    assert "not registered" in result.output
    assert not (tmp_path / "o").exists()
