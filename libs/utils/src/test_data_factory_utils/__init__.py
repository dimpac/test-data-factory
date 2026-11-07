"""Shared utilities for Test Data Factory applications."""

__version__ = "0.1.0"


def format_greeting(name: str = "world") -> str:
    """Return a greeting for the supplied name."""
    return f"Hello, {name}!"
