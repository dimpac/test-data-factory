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
