"""Command-line interface. Phase 1 stub.

Commands: metadata, profile, contract, generate, validate, repair, report.
"""

from __future__ import annotations

import click


@click.group()
def main() -> None:
    """Test Data Factory."""
