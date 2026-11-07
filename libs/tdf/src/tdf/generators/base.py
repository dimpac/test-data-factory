"""Generator interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from tdf.profiling.profiler import ProfileResult


class Generator(ABC):
    name: str

    @abstractmethod
    def generate(
        self,
        *,
        count: int,
        seed: int,
        columns: list[str],
        params: dict[str, Any],
        profile: ProfileResult | None = None,
    ) -> list[dict[str, Any]]:
        """Produce `count` rows keyed by column name. Same inputs give the same output."""
