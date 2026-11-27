"""Shapes of the published showcase files (specs/002 data-model.md, ADR-0007).

These models are the single definition: the JSON Schema in ``shared/schemas/`` and the
TypeScript types in ``shared/types/`` are generated from them. Rules that depend on
configuration (minimum sample, faster-alternative margin and saving) are checked when a
validation ``context`` carrying those values is given, as the publisher always does.
"""

from __future__ import annotations

import datetime as dt
import re
from typing import Annotated, Any, Literal, cast

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator, model_validator

from flight_pipeline.config import DisruptionNote

NonNegInt = Annotated[int, Field(ge=0)]
Share = Annotated[float, Field(ge=0.0, le=1.0)]
LocalMinute = Annotated[int, Field(ge=0, le=1439)]
Iata = Annotated[str, Field(pattern=r"^[A-Z0-9]{3}$")]
Airline = Annotated[str, Field(min_length=2, max_length=3)]

NOT_COVERED_KINDS: tuple[str, ...] = (
    "international",
    "two_or_more_stops",
    "separate_tickets",
    "non_reporting_airline",
    "outside_period",
    "not_in_showcase",
)
NotCoveredKind = Literal[
    "international",
    "two_or_more_stops",
    "separate_tickets",
    "non_reporting_airline",
    "outside_period",
    "not_in_showcase",
]
_SEMVER = re.compile(r"^\d+\.\d+\.\d+$")
_MONTH = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")
_RATE_TOLERANCE = 1e-6


class _Model(BaseModel):
    # published JSON always carries every field, so the schema marks defaulted ones required
    model_config = ConfigDict(
        extra="forbid", frozen=True, json_schema_serialization_defaults_required=True
    )


def _ctx(info: ValidationInfo, key: str) -> Any:
    context: object = info.context
    if isinstance(context, dict):
        return cast("dict[str, Any]", context).get(key)
    return None


# --- Common parts ------------------------------------------------------------------------


class DataPeriod(_Model):
    start: dt.date
    end: dt.date
    db1b_quarters: list[str]


class Rate(_Model):
    """Connection feasibility with its sample. The data period is the file's ``period``."""

    status: Literal["ok", "insufficient_data"]
    rate: Share | None
    paired_days: NonNegInt
    count_feasible: NonNegInt
    definition: Literal["connection_feasibility"]

    @model_validator(mode="after")
    def _consistent(self, info: ValidationInfo) -> Rate:
        if self.count_feasible > self.paired_days:
            raise ValueError("count_feasible exceeds paired_days")
        if self.status == "insufficient_data":
            if self.rate is not None:
                raise ValueError("insufficient_data carries no rate")
            return self
        if self.rate is None:
            raise ValueError("an ok status needs a rate")
        minimum = _ctx(info, "min_sample")
        if minimum is not None and self.paired_days < minimum:
            raise ValueError(f"ok status needs at least the minimum sample ({minimum} days)")
        if abs(self.rate - self.count_feasible / self.paired_days) > _RATE_TOLERANCE:
            raise ValueError("rate does not match count_feasible / paired_days")
        return self


# --- Itinerary parts ---------------------------------------------------------------------


class Schedule(_Model):
    dep_local_min: LocalMinute
    arr_local_min: LocalMinute
    layover_min: NonNegInt
    travel_min: Annotated[int, Field(ge=1)]
    nonstop_median_min: int | None
    nonstop_ratio: float | None


class FailureBreakdown(_Model):
    too_little_time: NonNegInt
    cancelled: NonNegInt
    diverted: NonNegInt
    dominant: Literal["too_little_time", "cancelled", "diverted", "none"]

    @model_validator(mode="after")
    def _dominant(self) -> FailureBreakdown:
        counts = {
            "too_little_time": self.too_little_time,
            "cancelled": self.cancelled,
            "diverted": self.diverted,
        }
        top = max(counts.values())
        expected = "none" if top == 0 else next(k for k, v in counts.items() if v == top)
        if self.dominant != expected:
            raise ValueError(f"dominant must be {expected}")
        return self


class DailySeries(_Model):
    """One entry per paired day: offset from the period start, actual slack in whole minutes
    (null for cancelled or diverted days) and an outcome code (F feasible, T too little time,
    C cancelled, D diverted), compact for the transfer-time slider (ADR-0006)."""

    day_offset: list[NonNegInt]
    slack_min: list[int | None]
    outcome: str

    @model_validator(mode="after")
    def _columns(self) -> DailySeries:
        n = len(self.day_offset)
        if len(self.slack_min) != n or len(self.outcome) != n:
            raise ValueError("day_offset, slack_min and outcome must have the same length")
        if any(b <= a for a, b in zip(self.day_offset, self.day_offset[1:], strict=False)):
            raise ValueError("day_offset must be strictly increasing")
        for code, slack in zip(self.outcome, self.slack_min, strict=True):
            if code not in "FTCD":
                raise ValueError(f"outcome code {code!r} is not one of F, T, C, D")
            if (code in "CD") != (slack is None):
                raise ValueError("slack_min is null exactly for cancelled or diverted days")
        return self


class ExcludedDays(_Model):
    not_connecting: NonNegInt
    quality: NonNegInt
    end_of_period: NonNegInt


class MonthRate(_Model):
    month: str
    status: Literal["ok", "insufficient_data", "no_flights"]
    rate: Share | None
    paired_days: NonNegInt
    note_ids: list[str]

    @field_validator("month")
    @classmethod
    def _month(cls, v: str) -> str:
        if not _MONTH.match(v):
            raise ValueError(f"month must be YYYY-MM, got {v!r}")
        return v

    @model_validator(mode="after")
    def _status(self) -> MonthRate:
        if (self.status == "ok") != (self.rate is not None):
            raise ValueError("rate is given exactly when status is ok")
        if self.status == "no_flights" and self.paired_days != 0:
            raise ValueError("no_flights months have no paired days")
        return self


class Buffer(_Model):
    """The recommended layover against the scheduled one. ``actual_layover_min`` is the
    median scheduled layover; ``scheduled_at_least_share`` is the share of operated days
    whose scheduled layover was at least the recommendation, since a median hides a layover
    that varies by day (review round 2)."""

    share: Annotated[float, Field(gt=0.5, lt=1.0)]
    needed_layover_min: NonNegInt | None
    actual_layover_min: NonNegInt
    scheduled_at_least_share: Share | None
    operated_days: NonNegInt


class Alternative(_Model):
    """A faster comparable itinerary whose feasibility is shown, by the paired interval, to
    be no more than the margin worse (research R8). Both rates carry their samples
    (Principle I): the alternative may not be in the same file."""

    itinerary_id: str
    minutes_saved: Annotated[int, Field(ge=1)]
    rate_this: Rate
    rate_other: Rate
    ci_low: float
    ci_high: float
    shared_days: NonNegInt

    @model_validator(mode="after")
    def _bounds(self, info: ValidationInfo) -> Alternative:
        if self.ci_low > self.ci_high:
            raise ValueError("ci_low must not exceed ci_high")
        margin = _ctx(info, "faster_margin")
        if margin is not None and self.ci_low < -margin - _RATE_TOLERANCE:
            raise ValueError("ci_low is below the equivalence margin")
        saving = _ctx(info, "faster_min_saving_min")
        if saving is not None and self.minutes_saved < saving:
            raise ValueError("minutes_saved is below the minimum saving")
        return self


class ConnectingOption(_Model):
    itinerary_id: str
    outbound_dep_local_min: LocalMinute
    rate: Rate
    better: bool
    ci_low: float | None
    ci_high: float | None

    @model_validator(mode="after")
    def _better(self) -> ConnectingOption:
        if self.better and (self.ci_low is None or self.ci_low <= 0):
            raise ValueError("better needs an interval above zero")
        return self


class ScheduleChange(_Model):
    date: dt.date
    leg: Literal["inbound", "outbound"]
    from_local_min: LocalMinute
    to_local_min: LocalMinute


class ScheduleWarnings(_Model):
    """The connection share with its sample: connecting days of the eligible days (days in
    the period less end-of-period days)."""

    connect_share: Share
    connecting_days: NonNegInt
    eligible_days: NonNegInt
    changes: list[ScheduleChange]

    @model_validator(mode="after")
    def _share(self) -> ScheduleWarnings:
        if self.connecting_days > self.eligible_days:
            raise ValueError("connecting_days exceeds eligible_days")
        if (
            self.eligible_days
            and abs(self.connect_share - self.connecting_days / self.eligible_days)
            > _RATE_TOLERANCE
        ):
            raise ValueError("connect_share does not match connecting_days / eligible_days")
        return self


class FindLeg(_Model):
    flight_number: str
    share_of_days: Share


class FindParams(_Model):
    origin: Iata
    dest: Iata
    airlines: list[Airline]
    legs: list[FindLeg]


class SoldRouting(_Model):
    passengers: NonNegInt
    routing_itineraries: Annotated[int, Field(ge=1)]


class ShowcaseItinerary(_Model):
    itinerary_id: str
    hub: Iata
    airline: Airline
    airline_out: Airline
    partner_connection: bool
    min_connection_min: NonNegInt  # the slider's default transfer time for this itinerary
    schedule: Schedule
    result: Rate
    failures: FailureBreakdown
    daily: DailySeries
    excluded_days: ExcludedDays
    monthly: list[MonthRate]
    buffer: Buffer
    faster_alternatives: list[Alternative]
    connecting_options: list[ConnectingOption]
    schedule_warnings: ScheduleWarnings
    find: FindParams
    tight_layover: bool
    sold: SoldRouting

    @model_validator(mode="after")
    def _series_matches_result(self) -> ShowcaseItinerary:
        """The daily series reproduces the default result and failure counts (SC-004)."""
        codes = self.daily.outcome
        if len(codes) != self.result.paired_days:
            raise ValueError("the daily series must have one entry per paired day")
        counts = (codes.count("F"), codes.count("T"), codes.count("C"), codes.count("D"))
        expected = (
            self.result.count_feasible,
            self.failures.too_little_time,
            self.failures.cancelled,
            self.failures.diverted,
        )
        if counts != expected:
            raise ValueError("the daily outcome codes do not match the result and failures")
        return self


class ShowcaseComparison(_Model):
    comparison_id: str
    itinerary_a: str
    itinerary_b: str
    difference: float
    ci_low: float
    ci_high: float
    shared_days: NonNegInt
    settings_compared: NonNegInt
    missing_settings_note: str
    cross_hub: bool
    landing: bool


class RouteFile(_Model):
    route_id: str
    period: DataPeriod
    itineraries: list[ShowcaseItinerary]
    comparisons: list[ShowcaseComparison]
    disruption_notes: list[DisruptionNote]

    @model_validator(mode="after")
    def _references(self) -> RouteFile:
        ids = {i.itinerary_id for i in self.itineraries}
        notes = {n.note_id for n in self.disruption_notes}
        for c in self.comparisons:
            if c.itinerary_a not in ids or c.itinerary_b not in ids:
                raise ValueError(f"comparison {c.comparison_id} refers to a missing itinerary")
        # faster alternatives and connecting options may name itineraries of the route
        # that are not in the file: their entries carry every figure shown
        for it in self.itineraries:
            if any(n not in notes for m in it.monthly for n in m.note_ids):
                raise ValueError(f"{it.itinerary_id} refers to a missing disruption note")
        return self


# --- Index -------------------------------------------------------------------------------


class Assumptions(_Model):
    min_connection_default_min: NonNegInt
    min_connection_partner_min: NonNegInt
    boarding_cutoff_min: NonNegInt
    recurrence_threshold: Share
    min_sample_days: Annotated[int, Field(ge=1)]
    monthly_min_sample: Annotated[int, Field(ge=1)]
    buffer_share: Annotated[float, Field(gt=0.5, lt=1.0)]
    faster_margin: Annotated[float, Field(ge=0.0, le=0.2)]
    faster_min_saving_min: Annotated[int, Field(ge=1)]


class AirlineCoverage(_Model):
    airline: Airline
    itineraries: NonNegInt
    sold_passengers: NonNegInt
    note: str = ""


class NotCovered(_Model):
    kind: NotCoveredKind
    text: str


class Coverage(_Model):
    routes: list[str]
    hubs: list[Iata]
    airlines: list[AirlineCoverage]
    period: DataPeriod
    not_covered: list[NotCovered]

    @model_validator(mode="after")
    def _every_kind(self) -> Coverage:
        kinds = [n.kind for n in self.not_covered]
        if sorted(kinds) != sorted(NOT_COVERED_KINDS):
            raise ValueError("not_covered must state each kind exactly once")
        return self


class RouteSummary(_Model):
    route_id: str
    origin: Iata
    dest: Iata
    regional_origin: bool
    itinerary_count: NonNegInt
    comparison_count: NonNegInt
    share_of_showcase: Share
    nonstop_median_min: int | None
    file: str


class LandingRef(_Model):
    route_id: str
    comparison_id: str
    reason: str


class Definition(_Model):
    key: str
    text: str
    methodology_anchor: str


class Attribution(_Model):
    source: str
    text: str
    licence: str
    url: str


class ManifestRef(_Model):
    """Pointer to manifest.json. Only identities that change the data are here, so the
    published bytes do not change with every code commit (the commit is in the manifest)."""

    code_version: str  # package version
    config_sha256: str
    manifest: str  # path of the manifest, relative to the output directory


class BalanceCaps(_Model):
    route: Share
    airline: Share
    hub: Share
    cross_hub_min: Share


class Balance(_Model):
    """The showcase's balance (FR-008): the caps, the resulting shares of showcase
    comparisons by airline and hub (a comparison counts for both itineraries' airlines and
    hubs), the cross-hub share, and any cap curation could not meet. Route shares are in
    ``routes[].share_of_showcase``."""

    caps: BalanceCaps
    airline_shares: dict[str, Share]
    hub_shares: dict[str, Share]
    cross_hub_share: Share
    shortfalls: list[str]


class ShowcaseIndex(_Model):
    schema_version: str
    period: DataPeriod
    assumptions: Assumptions
    coverage: Coverage
    balance: Balance
    routes: list[RouteSummary]
    landing: LandingRef
    definitions: list[Definition]
    attribution: list[Attribution]
    manifest: ManifestRef

    @field_validator("schema_version")
    @classmethod
    def _semver(cls, v: str) -> str:
        if not _SEMVER.match(v):
            raise ValueError(f"schema_version must be a semantic version, got {v!r}")
        return v

    @model_validator(mode="after")
    def _required_texts(self) -> ShowcaseIndex:
        sources = {a.source for a in self.attribution}
        missing = {"BTS", "airportsdata", "tzdata"} - sources
        if missing:
            raise ValueError(f"attribution is missing {sorted(missing)}")
        if "connection_feasibility" not in {d.key for d in self.definitions}:
            raise ValueError("definitions must include connection_feasibility")
        return self


class SourceRecord(_Model):
    name: str
    sha256: str
    pinned: bool


class ShowcaseManifest(_Model):
    sources: list[SourceRecord]
    config_sha256: str
    notes_sha256: str
    code_version: str
    git_commit: str
    packages: dict[str, str]
    outputs: dict[str, str]
    run: dict[str, Any]


PUBLISHED_MODELS: tuple[type[BaseModel], ...] = (ShowcaseIndex, RouteFile, ShowcaseManifest)


# --- Internal: the insights stage's output (derived insights.json, not published) ---------


class ItineraryInsights(_Model):
    failures: FailureBreakdown
    monthly: list[MonthRate]
    buffer: Buffer
    faster_alternatives: list[Alternative]
    connecting_options: list[ConnectingOption]
    schedule_warnings: ScheduleWarnings
    find: FindParams


class InsightsFile(_Model):
    """Every itinerary on a curated route, by itinerary id."""

    itineraries: dict[str, ItineraryInsights]
