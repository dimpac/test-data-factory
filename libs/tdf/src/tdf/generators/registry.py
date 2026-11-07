"""Generator registry. Phase 1 stub.

Required generators: sequence, integer, float, string, boolean, date, timestamp,
categorical, tuple, foreign_key. Also: faker (Faker provider values).
"""

from __future__ import annotations

import datetime as dt
import functools
import random
import string
from pathlib import Path
from typing import Any

from tdf.generators.base import Generator
from tdf.profiling.profiler import ProfileResult


class UnknownGeneratorError(KeyError):
    """No generator is registered under the name."""


def _faker_value(provider: str, seed: int, *, locale: str | None) -> Any:
    """One value from a Faker provider, seeded so the same inputs give the same value."""
    from faker import Faker

    fake = Faker(locale)
    fake.seed_instance(seed)
    method = getattr(fake, provider, None)
    if method is None:
        raise ValueError(f"Unknown Faker provider {provider!r}")
    return method()


# SteelWheels country names mapped to ISO alpha2 codes used by allCountriesCSV.csv.gz.
COUNTRY_CODES = {
    "Australia": "AU", "Austria": "AT", "Belgium": "BE", "Canada": "CA", "Denmark": "DK",
    "Finland": "FI", "France": "FR", "Germany": "DE", "Ireland": "IE", "Italy": "IT",
    "Japan": "JP", "Netherlands": "NL", "New Zealand": "NZ", "Norway": "NO",
    "Philippines": "PH", "Poland": "PL", "Portugal": "PT", "Russia": "RU",
    "Singapore": "SG", "South Africa": "ZA", "Spain": "ES", "Sweden": "SE",
    "Switzerland": "CH", "UK": "GB", "USA": "US",
}


# Sales territory per country. Source offices confirm AU=APAC, FR/UK=EMEA, JP=Japan, US=NA.
# The remaining entries follow the same regional grouping and are not in the source data.
TERRITORY_BY_COUNTRY = {
    "USA": "NA", "Canada": "NA",
    "Australia": "APAC", "New Zealand": "APAC", "Philippines": "APAC", "Singapore": "APAC",
    "Japan": "Japan",
    "UK": "EMEA", "France": "EMEA", "Germany": "EMEA", "Austria": "EMEA", "Belgium": "EMEA",
    "Denmark": "EMEA", "Finland": "EMEA", "Ireland": "EMEA", "Italy": "EMEA",
    "Netherlands": "EMEA", "Norway": "EMEA", "Poland": "EMEA", "Portugal": "EMEA",
    "Russia": "EMEA", "South Africa": "EMEA", "Spain": "EMEA", "Sweden": "EMEA",
    "Switzerland": "EMEA",
}


def _resolve_source(source: str) -> Path:
    """Resolve a data path as given, else relative to the working directory, else the repo root.

    Contracts name repository-relative paths such as ``data/allCountriesCSV.csv.gz``; resolving
    them against the repository root lets ``tdf`` run from any directory.
    """
    path = Path(source)
    if path.is_absolute() or path.exists():
        return path
    for parent in Path(__file__).resolve().parents:
        candidate = parent / source
        if candidate.exists():
            return candidate
    raise FileNotFoundError(f"geo source {source!r} not found (relative paths resolve against the "
                            f"working directory and the repository root)")


def _geo_pool(source: str, countries: list[str]) -> list[tuple[str, str, str, str]]:
    """(city, state, postal code, SteelWheels country) rows for the requested countries.

    `source` is a CSV, optionally gzip-compressed (``.gz``), with COUNTRY (alpha2), POSTAL_CODE,
    CITY and SHORT_STATE columns.
    """
    return list(_cached_geo_pool(str(_resolve_source(str(source))), tuple(countries)))


@functools.lru_cache(maxsize=8)
def _cached_geo_pool(source: str, countries: tuple[str, ...]) -> tuple[tuple[str, str, str, str], ...]:
    # The postal file has about 1.4M rows; read it once per (file, country set), not per call.
    import csv
    import gzip

    wanted = {COUNTRY_CODES[name]: name for name in countries}
    pool: list[tuple[str, str, str, str]] = []
    opener = gzip.open if source.endswith(".gz") else open
    with opener(source, "rt", newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            steelwheels_country = wanted.get(row["COUNTRY"])
            if steelwheels_country is None or not row["CITY"]:
                continue
            pool.append((row["CITY"], row["SHORT_STATE"], row["POSTAL_CODE"], steelwheels_country))
    return tuple(pool)


class _BuiltInGenerator(Generator):
    def __init__(self, name: str) -> None:
        self.name = name

    def generate(
        self,
        *,
        count: int,
        seed: int,
        columns: list[str],
        params: dict[str, Any],
        profile: ProfileResult | None = None,
    ) -> list[dict[str, Any]]:
        rng = random.Random(seed)
        rows: list[dict[str, Any]] = []

        if self.name == "geo":
            pool = _geo_pool(params["source"], list(params["countries"]))
            if not pool:
                raise ValueError(f"geo generator found no postal data for {params['countries']}")
            names = ("CITY", "STATE", "POSTALCODE", "COUNTRY")
            wanted = tuple(columns)
            if wanted not in (names, names + ("TERRITORY",)):
                raise ValueError(f"geo generator emits {names} (+TERRITORY), got {wanted}")
            rows = []
            for city, state, code, country in (rng.choice(pool) for _ in range(count)):
                row = dict(zip(names, (city, state, code, country)))
                if "TERRITORY" in wanted:
                    row["TERRITORY"] = TERRITORY_BY_COUNTRY[country]
                rows.append(row)
            return rows

        if self.name == "tuple":
            if profile is None:
                raise ValueError("tuple generator requires a profile")
            observation = next(
                (item for item in profile.observations
                 if item.metric == "value_set" and item.columns == columns),
                None,
            )
            if observation is None or not observation.value:
                raise ValueError(f"profile has no tuple value set for {columns}")
            if params.get("unique"):
                if count > len(observation.value):
                    raise ValueError(
                        f"unique tuple generation needs {count} observed combinations for {columns}, "
                        f"profile has {len(observation.value)}"
                    )
                chosen = rng.sample(observation.value, count)
            else:
                chosen = [rng.choice(observation.value) for _ in range(count)]
            return [dict(zip(columns, values)) for values in chosen]

        categorical_values: list[Any] | None = None
        categorical_weights: list[int] | None = None
        if self.name == "categorical":
            if params.get("source") == "profile":
                if profile is None:
                    raise ValueError("categorical generator requires a profile")
                observation = next(
                    (item for item in profile.observations
                     if item.metric == "value_frequencies" and item.columns == columns),
                    None,
                )
                if observation is None:
                    raise ValueError(f"profile has no frequencies for {columns}")
                categorical_values = list(observation.value)
                categorical_weights = list(observation.value.values())
            else:
                categorical_values = list(params.get("values", []))
            if not categorical_values:
                raise ValueError("categorical generator requires values")

        null_ratio = float(params.get("null_ratio", 0.0))
        start_date = end_date = dt.date(2000, 1, 1)
        date_span = 0
        if self.name in {"date", "timestamp"}:
            start_date = dt.date.fromisoformat(str(params.get("start", "2000-01-01"))[:10])
            end_date = dt.date.fromisoformat(str(params.get("end", "2030-12-31"))[:10])
            date_span = (end_date - start_date).days

        for index in range(count):
            row: dict[str, Any] = {}
            for column in columns:
                if null_ratio and rng.random() < null_ratio:
                    row[column] = None
                    continue
                if self.name == "sequence":
                    value: Any = int(params.get("start", 1)) + index
                    prefix = params.get("prefix")
                    row[column] = f"{prefix}{value}" if prefix is not None else value
                elif self.name == "integer":
                    row[column] = rng.randint(int(params.get("min", 0)), int(params.get("max", 10_000)))
                elif self.name == "float":
                    row[column] = rng.uniform(float(params.get("min", 0.0)), float(params.get("max", 1.0)))
                elif self.name == "string":
                    length = int(params.get("length", 12))
                    row[column] = "".join(rng.choices(string.ascii_letters + string.digits, k=length))
                elif self.name == "boolean":
                    row[column] = bool(rng.getrandbits(1))
                elif self.name == "date":
                    row[column] = start_date + dt.timedelta(days=rng.randint(0, date_span))
                elif self.name == "timestamp":
                    seconds = date_span * 86_400 + 86_399
                    row[column] = dt.datetime.combine(start_date, dt.time()) + dt.timedelta(
                        seconds=rng.randint(0, seconds)
                    )
                elif self.name == "categorical":
                    row[column] = rng.choices(
                        categorical_values, weights=categorical_weights, k=1
                    )[0]
                elif self.name == "faker":
                    if "provider" not in params:
                        raise ValueError("faker generator requires a 'provider' param")
                    row[column] = _faker_value(params["provider"], rng.getrandbits(32), locale=params.get("locale"))
                elif self.name == "foreign_key":
                    row[column] = None
                else:
                    raise UnknownGeneratorError(self.name)
            rows.append(row)
        return rows


_NAMES = {
    "sequence", "integer", "float", "string", "boolean", "date", "timestamp",
    "categorical", "tuple", "foreign_key", "faker", "geo",
}
_GENERATORS = {name: _BuiltInGenerator(name) for name in _NAMES}


def available_generators() -> set[str]:
    return set(_GENERATORS)


def get_generator(name: str) -> Generator:
    try:
        return _GENERATORS[name]
    except KeyError as exc:
        raise UnknownGeneratorError(name) from exc
