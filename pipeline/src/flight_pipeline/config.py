"""Pinned configuration: Pydantic models and TOML loading (contracts/config.md, research R9).

Every value is required in the file; there are no hidden defaults. Relative paths resolve
against the repository root, which is the parent of the config file's directory.
"""

from __future__ import annotations

import datetime as dt
import re
import tomllib
from pathlib import Path
from typing import Annotated, Any, Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

Share = Annotated[float, Field(ge=0.0, le=1.0)]
Minutes = Annotated[int, Field(ge=0)]
Season = Literal["winter", "spring", "summer", "autumn"]
SEASONS: tuple[Season, ...] = ("winter", "spring", "summer", "autumn")

_MONTH_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


class ConfigError(ValueError):
    """Raised when the configuration file is missing values or breaks a validation rule."""


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


def _parse_month(value: str) -> tuple[int, int]:
    year, month = value.split("-")
    return int(year), int(month)


def _months_between(start: str, end: str) -> list[tuple[int, int]]:
    y, m = _parse_month(start)
    ey, em = _parse_month(end)
    out: list[tuple[int, int]] = []
    while (y, m) <= (ey, em):
        out.append((y, m))
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


def _month_dates(months: list[tuple[int, int]]) -> tuple[dt.date, dt.date]:
    (sy, sm), (ey, em) = months[0], months[-1]
    first_next = dt.date(ey + 1, 1, 1) if em == 12 else dt.date(ey, em + 1, 1)
    return dt.date(sy, sm, 1), first_next - dt.timedelta(days=1)


class Paths(_Strict):
    raw_dir: str
    derived_dir: str
    reports_dir: str


class Period(_Strict):
    """One period for every source (amendment 1, research R11): exactly 12 months, in whole
    quarters."""

    start: str
    end: str

    @field_validator("start", "end")
    @classmethod
    def _month_format(cls, v: str) -> str:
        if not _MONTH_RE.match(v):
            raise ValueError(f"must be YYYY-MM, got {v!r}")
        return v

    @model_validator(mode="after")
    def _twelve_months_in_quarters(self) -> Period:
        n = len(_months_between(self.start, self.end))
        if n != 12:
            raise ValueError(f"period must be exactly 12 months, got {n}")
        if _parse_month(self.start)[1] not in (1, 4, 7, 10):
            raise ValueError("period must start and end on quarter boundaries")
        return self

    def months(self) -> list[tuple[int, int]]:
        return _months_between(self.start, self.end)

    def quarters(self) -> list[tuple[int, int]]:
        """(year, quarter) for each quarter in the period."""
        return [(y, (m - 1) // 3 + 1) for y, m in self.months() if m in (1, 4, 7, 10)]

    def dates(self) -> tuple[dt.date, dt.date]:
        return _month_dates(self.months())

    def days(self) -> int:
        start, end = self.dates()
        return (end - start).days + 1


class OnTimeSourceConfig(_Strict):
    url_pattern: str
    overrides: dict[str, str]
    checksums: dict[str, str]

    @field_validator("url_pattern")
    @classmethod
    def _placeholders(cls, v: str) -> str:
        for placeholder in ("{year}", "{month}"):
            if placeholder not in v:
                raise ValueError(f"url_pattern must contain {placeholder.strip('{}')} placeholder")
        return v

    @field_validator("overrides", "checksums")
    @classmethod
    def _month_keys(cls, v: dict[str, str]) -> dict[str, str]:
        for key in v:
            if not _MONTH_RE.match(key):
                raise ValueError(f"keys must be YYYY-MM, got {key!r}")
        return v


_QUARTER_RE = re.compile(r"^\d{4}-[1-4]$")


class Db1bSourceConfig(_Strict):
    url_pattern: str
    checksums: dict[str, str]

    @field_validator("url_pattern")
    @classmethod
    def _placeholders(cls, v: str) -> str:
        for placeholder in ("{year}", "{quarter}"):
            if placeholder not in v:
                raise ValueError(f"url_pattern must contain {placeholder.strip('{}')} placeholder")
        return v

    @field_validator("checksums")
    @classmethod
    def _quarter_keys(cls, v: dict[str, str]) -> dict[str, str]:
        for key in v:
            if not _QUARTER_RE.match(key):
                raise ValueError(f"keys must be YYYY-Q, got {key!r}")
        return v


class T100SourceConfig(_Strict):
    manual_file: str
    checksum: str


class Sources(_Strict):
    ontime: OnTimeSourceConfig
    db1b: Db1bSourceConfig
    t100: T100SourceConfig


class TimezoneOverride(_Strict):
    tz: str
    source: str

    @field_validator("tz")
    @classmethod
    def _valid_zone(cls, v: str) -> str:
        try:
            ZoneInfo(v)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError(f"unknown IANA time zone {v!r}") from exc
        return v


class Timezones(_Strict):
    overrides: dict[str, TimezoneOverride]


class HubWeights(_Strict):
    airlines: Annotated[float, Field(ge=0.0)]
    departures: Annotated[float, Field(ge=0.0)]
    passengers: Annotated[float, Field(ge=0.0)]

    @model_validator(mode="after")
    def _some_positive(self) -> HubWeights:
        if self.airlines + self.departures + self.passengers <= 0:
            raise ValueError("weights must not all be zero")
        return self


class Hubs(_Strict):
    candidate_pool_size: Annotated[int, Field(ge=1)]
    airline_share_min: Share
    eligible_itineraries_min: Annotated[int, Field(ge=0)]
    weights: HubWeights
    count: Annotated[int, Field(ge=5, le=8)]
    major_networks: list[str]
    winter_months: list[int]
    spring_months: list[int]
    summer_months: list[int]
    autumn_months: list[int]
    min_winter_peak: Annotated[int, Field(ge=0)]
    min_summer_peak: Annotated[int, Field(ge=0)]

    @model_validator(mode="after")
    def _seasons_partition_year(self) -> Hubs:
        months = self.winter_months + self.spring_months + self.summer_months + self.autumn_months
        if sorted(months) != list(range(1, 13)):
            raise ValueError("season month lists must contain each month 1-12 exactly once")
        if self.count > self.candidate_pool_size:
            raise ValueError("count must not exceed candidate_pool_size")
        return self

    def season_of(self, month: int) -> Season:
        for season, months in zip(
            SEASONS,
            (self.winter_months, self.spring_months, self.summer_months, self.autumn_months),
            strict=True,
        ):
            if month in months:
                return season
        raise ValueError(f"month {month} is not in any season")


class Itineraries(_Strict):
    min_connection_default_min: Minutes
    min_connection_partner_min: Minutes
    min_connection_by_hub: dict[str, Minutes]
    max_layover_min: Annotated[int, Field(ge=1, lt=1440)]
    recurrence_threshold: Share
    partners: list[list[str]]
    min_sold_passengers: Annotated[int, Field(ge=0)]
    carrier_map: dict[str, str]

    @field_validator("carrier_map")
    @classmethod
    def _codes(cls, v: dict[str, str]) -> dict[str, str]:
        for key, value in v.items():
            if not (2 <= len(key) <= 3 and 2 <= len(value) <= 3):
                raise ValueError(
                    f"carrier_map entries must be airline codes, got {key!r}: {value!r}"
                )
        return v

    @field_validator("partners")
    @classmethod
    def _pairs(cls, v: list[list[str]]) -> list[list[str]]:
        for pair in v:
            if len(pair) != 2 or pair[0] == pair[1]:
                raise ValueError(f"partners entries must be two different airlines, got {pair}")
        return v

    def min_connection_for(self, hub: str, *, partner: bool) -> int:
        """Minimum scheduled layover at a hub. Partner connections use the larger of the
        hub's minimum and the partner minimum."""
        base = self.min_connection_by_hub.get(hub, self.min_connection_default_min)
        return max(base, self.min_connection_partner_min) if partner else base

    def partner_set(self) -> frozenset[frozenset[str]]:
        return frozenset(frozenset(p) for p in self.partners)


class Feasibility(_Strict):
    boarding_cutoff_min: Minutes
    min_sample_days: Annotated[int, Field(ge=1)]


class Selection(_Strict):
    od_pairs_count: Annotated[int, Field(ge=10, le=15)]
    regional_share_min: Share
    max_pairs_per_hub: Annotated[int, Field(ge=1)]


class Comparison(_Strict):
    travel_time_tolerance_min: Minutes
    departure_window_min: Annotated[int, Field(ge=0, le=720)]
    showcase_gap: Share
    ci_level: Annotated[float, Field(gt=0.0, lt=1.0)]
    bootstrap_resamples: Annotated[int, Field(ge=100)]
    go_min_examples: Annotated[int, Field(ge=1)]
    go_min_hubs: Annotated[int, Field(ge=1)]


class Sensitivity(_Strict):
    min_connection_min: list[Minutes]
    boarding_cutoff_min: list[Minutes]
    recurrence_threshold: list[Share]

    @field_validator("min_connection_min", "boarding_cutoff_min", "recurrence_threshold")
    @classmethod
    def _at_least_three(cls, v: list[Any]) -> list[Any]:
        if len(v) < 3 or len(set(v)) != len(v):
            raise ValueError("needs at least 3 distinct values (FR-027)")
        return v


class Quality(_Strict):
    clock_mismatch_max_share: Share


class Runtime(_Strict):
    limit_min: Annotated[float, Field(gt=0)]


class Config(_Strict):
    seed: int
    paths: Paths
    period: Period
    sources: Sources
    timezones: Timezones
    hubs: Hubs
    itineraries: Itineraries
    feasibility: Feasibility
    selection: Selection
    comparison: Comparison
    sensitivity: Sensitivity
    quality: Quality
    runtime: Runtime
    repo_root: Path = Field(exclude=True)

    @model_validator(mode="after")
    def _defaults_in_sensitivity(self) -> Config:
        checks = (
            (
                "min_connection_min",
                self.itineraries.min_connection_default_min,
                self.sensitivity.min_connection_min,
            ),
            (
                "boarding_cutoff_min",
                self.feasibility.boarding_cutoff_min,
                self.sensitivity.boarding_cutoff_min,
            ),
            (
                "recurrence_threshold",
                self.itineraries.recurrence_threshold,
                self.sensitivity.recurrence_threshold,
            ),
        )
        for name, default, values in checks:
            if default not in values:
                raise ValueError(f"sensitivity.{name} must include the default value {default}")
        return self

    def path(self, value: str) -> Path:
        p = Path(value)
        return p if p.is_absolute() else self.repo_root / p


def _format_errors(exc: ValidationError) -> str:
    parts: list[str] = []
    for err in exc.errors():
        loc = ".".join(str(x) for x in err["loc"] if not isinstance(x, int))
        msg = err["msg"]
        if err["type"] == "extra_forbidden":
            msg = "unknown key"
        elif err["type"] == "missing":
            msg = "required key is missing"
        parts.append(f"{loc}: {msg}" if loc else msg)
    return "; ".join(parts)


def parse_config(data: dict[str, Any], repo_root: Path) -> Config:
    """Validate a parsed TOML document."""
    if "repo_root" in data:
        raise ConfigError("repo_root: unknown key")
    try:
        return Config.model_validate({**data, "repo_root": repo_root})
    except ValidationError as exc:
        raise ConfigError(f"invalid configuration: {_format_errors(exc)}") from exc


def load_config(path: Path) -> Config:
    """Load and validate the TOML config file at ``path``."""
    path = path.resolve()
    try:
        with path.open("rb") as f:
            data = tomllib.load(f)
    except FileNotFoundError as exc:
        raise ConfigError(f"config file not found: {path}") from exc
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"config file is not valid TOML: {exc}") from exc
    return parse_config(data, path.parent.parent)
