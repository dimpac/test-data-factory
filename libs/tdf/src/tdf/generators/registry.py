"""Generator registry. Phase 1 stub.

Required generators: sequence, integer, float, string, boolean, date, timestamp,
categorical, tuple, foreign_key.
"""

from __future__ import annotations

from tdf.generators.base import Generator


class UnknownGeneratorError(KeyError):
    """No generator is registered under the name."""


def available_generators() -> set[str]:
    raise NotImplementedError


def get_generator(name: str) -> Generator:
    raise NotImplementedError
