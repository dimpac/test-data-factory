"""Command-line interface for the Phase 1 test data factory."""

from __future__ import annotations

from pathlib import Path

import click
import duckdb

from tdf.contracts import ContractFile, load_contract_file, validate_contract
from tdf.engine import generate_dataset
from tdf.graph import GraphClient
from tdf.metadata import MetadataRepository, check_schema, introspect_duckdb, load_erd
from tdf.output import write_csv
from tdf.profiling import ProfileResult, profile_table
from tdf.validation import Outcome, validate_dataset


@click.group()
def main() -> None:
    """Contract-driven synthetic test data generation."""


@main.group()
def metadata() -> None:
    """Register and inspect database metadata."""


@metadata.command("register")
@click.option("--database", required=True)
@click.option("--erd", type=click.Path(exists=True, dir_okay=False, path_type=Path), required=True)
@click.option("--source", type=click.Path(exists=True, dir_okay=False, path_type=Path), required=True)
def metadata_register(database: str, erd: Path, source: Path) -> None:
    """Register an ERD and its physical DuckDB schema."""
    schema = load_erd(erd)
    physical = introspect_duckdb(source)
    errors = [issue for issue in check_schema(schema, physical) if issue.severity == "error"]
    if errors:
        raise click.ClickException("; ".join(issue.message for issue in errors))
    graph = GraphClient.from_env()
    try:
        MetadataRepository(graph).register_database(database, schema, physical)
    finally:
        graph.close()
    click.echo(f"Registered {database}")


def _profile_options(repository: MetadataRepository, database: str, table: str) -> tuple[list[list[str]], list[str]]:
    """Tuple column lists and opted-in value-set columns declared by the table's stored contract."""
    try:
        contract = repository.load_contract(database, table)
    except KeyError:
        return [], []
    tuple_sets: list[list[str]] = []
    value_set_columns: list[str] = []
    for policy in contract.policies:
        for group in policy.column_groups:
            if group.generator == "tuple":
                tuple_sets.append(group.columns)
            if group.params.get("value_set"):
                value_set_columns.extend(group.columns)
    return tuple_sets, value_set_columns


@main.command()
@click.option("--database", required=True)
@click.option("--source", type=click.Path(exists=True, dir_okay=False, path_type=Path), required=True)
@click.option("--table", required=True)
def profile(database: str, source: Path, table: str) -> None:
    """Profile one source table and save its observations."""
    graph = GraphClient.from_env()
    try:
        repository = MetadataRepository(graph)
        schema = repository.get_schema(database)
        if table not in schema.tables:
            raise click.ClickException(f"Unknown table {table}")
        tuple_sets, value_set_columns = _profile_options(repository, database, table)
        with duckdb.connect(str(source), read_only=True) as connection:
            result = profile_table(
                connection, table, tuple_sets=tuple_sets, value_set_columns=value_set_columns
            )
        repository.save_profile(database, result)
    finally:
        graph.close()
    click.echo(f"Profiled {table}: {result.id}")


@main.group(name="contract")
def contract_group() -> None:
    """Load and inspect generator contracts."""


@contract_group.command("load")
@click.argument("path", type=click.Path(exists=True, dir_okay=False, path_type=Path))
def contract_load(path: Path) -> None:
    """Validate and persist a contract file."""
    contract_file = load_contract_file(path)
    graph = GraphClient.from_env()
    try:
        repository = MetadataRepository(graph)
        schema = repository.get_schema(contract_file.database)
        for contract in contract_file.contracts:
            validate_contract(contract, schema)
            repository.save_contract(contract_file.database, contract)
    finally:
        graph.close()
    click.echo(f"Loaded {len(contract_file.contracts)} contracts")


def _parse_row_counts(values: tuple[str, ...]) -> dict[str, int]:
    result: dict[str, int] = {}
    for value in values:
        try:
            table, count = value.split("=", 1)
            result[table] = int(count)
        except ValueError as exc:
            raise click.BadParameter(f"Expected TABLE=COUNT, got {value!r}", param_hint="--rows") from exc
    return result


@main.command()
@click.option("--database")
@click.option("--contract", "contract_path", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--erd", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--seed", type=int, default=42, show_default=True)
@click.option("--out", type=click.Path(file_okay=False, path_type=Path), required=True)
@click.option("--rows", multiple=True, metavar="TABLE=COUNT")
def generate(
    database: str | None,
    contract_path: Path | None,
    erd: Path | None,
    seed: int,
    out: Path,
    rows: tuple[str, ...],
) -> None:
    """Generate CSV files from stored metadata or a contract file."""
    profiles: dict[str, ProfileResult] = {}
    if contract_path:
        contract_file = load_contract_file(contract_path)
        if erd is None:
            raise click.ClickException("--erd is required with --contract")
        schema = load_erd(erd)
    else:
        if not database:
            raise click.ClickException("--database is required when --contract is not supplied")
        graph = GraphClient.from_env()
        try:
            repository = MetadataRepository(graph)
            schema = repository.get_schema(database)
            contracts = [repository.load_contract(database, table) for table in schema.tables]
            contract_file = ContractFile(database=database, contracts=contracts)
            for table in schema.tables:
                try:
                    profiles[table] = repository.get_profile(database, table)
                except KeyError:
                    pass
        finally:
            graph.close()
    data = generate_dataset(
        contract_file, schema, seed=seed, profiles=profiles,
        row_counts=_parse_row_counts(rows),
    )
    out.mkdir(parents=True, exist_ok=True)
    for table, table_rows in data.items():
        columns = [column.name for column in schema.tables[table].columns]
        write_csv(out / f"{table}.csv", columns, table_rows)
    click.echo(f"Generated {sum(map(len, data.values()))} rows in {out}")


@main.command(name="validate")
@click.option("--database", required=True)
@click.option("--data-dir", type=click.Path(exists=True, file_okay=False, path_type=Path), required=True)
def validate_command(database: str, data_dir: Path) -> None:
    """Validate generated CSV files independently from generation."""
    graph = GraphClient.from_env()
    try:
        repository = MetadataRepository(graph)
        schema = repository.get_schema(database)
        expectations = []
        for table in schema.tables:
            contract = repository.load_contract(database, table)
            profile_result = None
            try:
                profile_result = repository.get_profile(database, table)
            except KeyError:
                pass
            for policy in contract.policies:
                if policy.intent != "FUNCTIONAL":
                    continue
                for expectation in policy.expectations:
                    if expectation.params.get("source") == "profile" and profile_result:
                        params = dict(expectation.params)
                        observation = next(
                            (item for item in profile_result.observations
                             if item.metric == "value_set" and
                             item.columns == expectation.target.columns),
                            None,
                        )
                        if observation:
                            params["values"] = observation.value
                        expectation = expectation.model_copy(update={"params": params})
                    expectations.append(expectation)
    finally:
        graph.close()
    results = validate_dataset(data_dir, schema, expectations)
    for result in results:
        suffix = f" {result.evidence}" if result.evidence else ""
        click.echo(f"{result.expectation_id}: {result.outcome}{suffix}")
    if any(result.outcome is Outcome.UNEXPECTED_VIOLATION for result in results):
        raise click.ClickException("Dataset validation failed")


@main.command()
def repair() -> None:
    """Repair metadata or contracts (not available in Phase 1)."""
    raise click.ClickException("Repair is not available in Phase 1")


@main.command()
def report() -> None:
    """Report generation and validation status."""
    click.echo("No report has been generated")
