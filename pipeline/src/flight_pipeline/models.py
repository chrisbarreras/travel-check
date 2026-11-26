"""Pydantic models for every table and report (data-model.md, ADR-0007).

Storage convention: Parquet timestamp columns are naive and always mean UTC. ``validate_table``
attaches UTC when reading them back, so results never depend on the host time zone.
"""

from __future__ import annotations

import datetime as dt
import re
from collections.abc import Iterable, Sequence
from typing import Annotated, Any, Literal

import duckdb
from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    TypeAdapter,
    field_validator,
    model_validator,
)

Airline = Annotated[str, Field(min_length=2, max_length=3)]
Iata = Annotated[str, Field(pattern=r"^[A-Z0-9]{3}$")]
NonNegInt = Annotated[int, Field(ge=0)]
Share = Annotated[float, Field(ge=0.0, le=1.0)]
LocalMinute = Annotated[int, Field(ge=0, le=1439)]
Season = Literal["winter", "spring", "summer", "autumn"]

QualityFlag = Literal[
    "ok", "duplicate", "conflicting_duplicate", "missing_actual_times", "clock_time_mismatch"
]
Outcome = Literal["feasible", "insufficient_time", "cancelled", "diverted"]
Decision = Literal["go", "no_go", "pivot"]


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


def _require_utc(value: dt.datetime | None, name: str) -> None:
    if value is not None and value.utcoffset() != dt.timedelta(0):
        raise ValueError(f"{name} must be in UTC")


# --- Source-level entities ---------------------------------------------------------------


class FlightRecord(_Model):
    marketing_airline: Airline
    operating_airline: Airline
    flight_number: Annotated[int, Field(ge=1)]
    service_date: dt.date
    origin: Iata
    dest: Iata
    sched_dep_utc: AwareDatetime
    sched_arr_utc: AwareDatetime
    sched_dep_local_min: LocalMinute
    sched_arr_local_min: LocalMinute
    sched_elapsed_min: Annotated[int, Field(ge=1)]
    actual_dep_utc: AwareDatetime | None
    actual_arr_utc: AwareDatetime | None
    cancelled: bool
    diverted: bool
    cancellation_code: Literal["A", "B", "C", "D"] | None
    weather_delay_min: NonNegInt | None
    weather_affected: bool
    quality_flag: QualityFlag

    @model_validator(mode="after")
    def _rules(self) -> FlightRecord:
        for name in ("sched_dep_utc", "sched_arr_utc", "actual_dep_utc", "actual_arr_utc"):
            _require_utc(getattr(self, name), name)
        if self.sched_arr_utc <= self.sched_dep_utc:
            raise ValueError("sched_arr_utc must be after sched_dep_utc")
        operated = not self.cancelled and not self.diverted
        if (
            operated
            and self.quality_flag == "ok"
            and (self.actual_dep_utc is None or self.actual_arr_utc is None)
        ):
            raise ValueError("actual times are required for an operated flight flagged ok")
        return self


class PassengerTraffic(_Model):
    year: Annotated[int, Field(ge=1990, le=2100)]
    month: Annotated[int, Field(ge=1, le=12)]
    origin: Iata
    carrier: Airline
    passengers: NonNegInt


class SoldRouting(_Model):
    """A one-connection routing sold in DB1B Market, summed over the period (FR-013a)."""

    origin: Iata
    hub: Iata
    dest: Iata
    airline_in: Airline
    airline_out: Airline
    passengers: NonNegInt


AirportRole = Literal["hub", "candidate", "regional", "other"]


class Airport(_Model):
    code: Iata
    tz: str
    role: AirportRole


# --- Hub selection -----------------------------------------------------------------------


class SeasonShares(_Model):
    winter: Share | None
    spring: Share | None
    summer: Share | None
    autumn: Share | None


class HubCandidate(_Model):
    airport: Iata
    departures: NonNegInt
    airline_count: NonNegInt
    airlines: list[Airline]
    passengers: NonNegInt | None
    weather_share: Share
    weather_share_by_season: SeasonShares
    weather_peak_season: Season | Literal["unknown"]
    eligible_itineraries: NonNegInt
    eligible: bool
    score: Annotated[float, Field(ge=0.0)]
    rank: Annotated[int, Field(ge=1)]

    @model_validator(mode="after")
    def _airline_count(self) -> HubCandidate:
        if self.airline_count != len(self.airlines):
            raise ValueError("airline_count must equal the number of airlines")
        return self


_REASON_RE = re.compile(
    r"^(score|airline_coverage:[A-Z0-9]{2,3}|weather_winter|weather_summer"
    r"|weather_above_median|weather_below_median)$"
)


class HubSelection(_Model):
    airport: Iata
    selected: bool
    reason: str | None

    @model_validator(mode="after")
    def _reason(self) -> HubSelection:
        if self.selected:
            if self.reason is None or not _REASON_RE.match(self.reason):
                raise ValueError(f"selected hub needs a valid reason, got {self.reason!r}")
        elif self.reason is not None:
            raise ValueError("reason must be null when not selected")
        return self


# --- Itineraries -------------------------------------------------------------------------


class PatternKey(_Model):
    marketing_airline: Airline
    flight_number: Annotated[int, Field(ge=1)]
    origin: Iata
    dest: Iata


class FlightPattern(_Model):
    marketing_airline: Airline
    flight_number: Annotated[int, Field(ge=1)]
    origin: Iata
    dest: Iata
    scheduled_days: NonNegInt
    recurrence: Share


class FlightNumberShare(_Model):
    flight_number: str
    share_of_days: Share


class ScheduleSlot(_Model):
    """A cluster of one airline's flights on one route at about the same local time
    (ADR-0014, specs/002 data-model.md)."""

    slot_id: str
    marketing_airline: Airline
    origin: Iata
    dest: Iata
    ref_dep_local_min: LocalMinute
    min_dep_local_min: LocalMinute
    max_dep_local_min: LocalMinute
    scheduled_days: Annotated[int, Field(ge=1)]
    recurrence: Share
    flight_numbers: list[FlightNumberShare]

    @model_validator(mode="after")
    def _shape(self) -> ScheduleSlot:
        if not self.slot_id.startswith(f"{self.marketing_airline}-{self.origin}-{self.dest}-"):
            raise ValueError("slot_id must start with airline, origin and destination")
        if not self.min_dep_local_min <= self.ref_dep_local_min <= self.max_dep_local_min:
            raise ValueError("reference time must lie within the slot's range")
        return self


class SlotDay(_Model):
    slot_id: str
    service_date: dt.date
    marketing_airline: Airline
    flight_number: Annotated[int, Field(ge=1)]
    origin: Iata
    dest: Iata
    dep_local_min: LocalMinute


class SlotChange(_Model):
    slot_id: str
    change_date: dt.date
    from_local_min: LocalMinute
    to_local_min: LocalMinute


class NonstopMedian(_Model):
    origin: Iata
    dest: Iata
    nonstop_median_min: Annotated[int, Field(ge=1)]
    nonstop_days: Annotated[int, Field(ge=1)]


class Itinerary(_Model):
    """A slot pair through a hub (ADR-0014; specs/002 data-model.md)."""

    itinerary_id: str
    origin: Iata
    hub: Iata
    dest: Iata
    inbound_slot: str
    outbound_slot: str
    airline_in: Airline
    airline_out: Airline
    partner_connection: bool
    median_layover_min: NonNegInt
    median_travel_min: Annotated[int, Field(ge=1)]
    median_dep_local_min: LocalMinute
    connect_share: Share
    eligible_days: NonNegInt
    sold_passengers: NonNegInt
    routing_itineraries: Annotated[int, Field(ge=1)]

    @model_validator(mode="after")
    def _shape(self) -> Itinerary:
        if self.origin == self.dest:
            raise ValueError("origin and dest must differ")
        if not self.inbound_slot.startswith(f"{self.airline_in}-{self.origin}-{self.hub}-"):
            raise ValueError("inbound slot must fly origin -> hub for airline_in")
        if not self.outbound_slot.startswith(f"{self.airline_out}-{self.hub}-{self.dest}-"):
            raise ValueError("outbound slot must fly hub -> dest for airline_out")
        if (self.airline_in != self.airline_out) != self.partner_connection:
            raise ValueError("partner_connection must be true exactly when airlines differ")
        if not self.itinerary_id.startswith(f"{self.origin}-{self.hub}-{self.dest}:"):
            raise ValueError("itinerary_id does not match its route")
        return self


# --- Outcomes and results ----------------------------------------------------------------


class DailyOutcome(_Model):
    itinerary_id: str
    service_date: dt.date
    raw_slack_min: int | None
    outcome: Outcome

    @model_validator(mode="after")
    def _slack(self) -> DailyOutcome:
        failed_leg = self.outcome in ("cancelled", "diverted")
        if failed_leg != (self.raw_slack_min is None):
            raise ValueError("raw_slack_min is null exactly when a leg was cancelled or diverted")
        return self


class ItineraryResult(_Model):
    itinerary_id: str
    scenario_id: str
    paired_days: NonNegInt
    excluded_not_connecting: NonNegInt
    excluded_quality: NonNegInt
    excluded_end_of_period: NonNegInt
    feasibility_rate: Share | None
    status: Literal["ok", "insufficient_data"]
    count_feasible: NonNegInt
    count_insufficient_time: NonNegInt
    count_cancelled: NonNegInt
    count_diverted: NonNegInt
    slack_min: int | None
    slack_p10: int | None
    slack_p50: int | None
    slack_p90: int | None
    period_start: dt.date
    period_end: dt.date

    @model_validator(mode="after")
    def _rules(self) -> ItineraryResult:
        if (self.status == "insufficient_data") != (self.feasibility_rate is None):
            raise ValueError(
                "feasibility_rate must be null exactly when status is insufficient_data"
            )
        total = (
            self.count_feasible
            + self.count_insufficient_time
            + self.count_cancelled
            + self.count_diverted
        )
        if total != self.paired_days:
            raise ValueError("outcome counts must sum to paired_days")
        if self.period_end < self.period_start:
            raise ValueError("period_end must not precede period_start")
        return self


class SensitivityScenario(_Model):
    scenario_id: str
    min_connection_min: NonNegInt
    boarding_cutoff_min: NonNegInt
    recurrence_threshold: Share
    is_default: bool


def validate_scenarios(scenarios: Sequence[SensitivityScenario]) -> None:
    defaults = sum(1 for s in scenarios if s.is_default)
    if defaults != 1:
        raise ValueError(f"exactly one scenario must be the default, found {defaults}")
    ids = [s.scenario_id for s in scenarios]
    if len(set(ids)) != len(ids):
        raise ValueError("scenario_id values must be unique")


class OdSelection(_Model):
    origin: Iata
    dest: Iata
    comparable_pairs: NonNegInt
    main_hub: Iata
    regional_origin: bool
    rank: Annotated[int, Field(ge=1)]
    selected: bool


class OdExclusions(_Model):
    """Candidates removed by each itinerary rule, in order, for one pair (FR-018a)."""

    origin: Iata
    dest: Iata
    candidates: NonNegInt
    excluded_bounds: NonNegInt
    excluded_unsold: NonNegInt
    excluded_not_connecting: NonNegInt
    excluded_recurrence: NonNegInt
    qualifying: NonNegInt

    @model_validator(mode="after")
    def _adds_up(self) -> OdExclusions:
        removed = (
            self.excluded_bounds
            + self.excluded_unsold
            + self.excluded_not_connecting
            + self.excluded_recurrence
        )
        if self.candidates - removed != self.qualifying:
            raise ValueError("qualifying must equal candidates minus all exclusions")
        return self


class ComparablePair(_Model):
    itinerary_a: str
    itinerary_b: str
    travel_diff_min: NonNegInt
    dep_diff_min: NonNegInt
    rate_diff: float | None
    scenarios_compared: NonNegInt
    settings_compared: NonNegInt
    shared_days: NonNegInt
    ci_low: float | None
    ci_high: float | None
    assumption_sensitive: bool
    showcase: bool

    @model_validator(mode="after")
    def _interval(self) -> ComparablePair:
        if self.ci_low is not None and self.ci_high is not None and self.ci_low > self.ci_high:
            raise ValueError("ci_low must not exceed ci_high")
        return self


class CuratedRouteRow(_Model):
    """derived showcase_routes.parquet: one showcase route (specs/002 research R4)."""

    route_id: str
    origin: Iata
    dest: Iata
    regional_origin: bool
    rank: Annotated[int, Field(ge=1)]
    itinerary_count: NonNegInt
    comparison_count: NonNegInt
    share_of_showcase: Share


class CuratedComparisonRow(_Model):
    """derived showcase_comparisons.parquet: one showcase comparison kept by curation."""

    comparison_id: str
    route_id: str
    itinerary_a: str
    itinerary_b: str
    cross_hub: bool
    difference: float
    landing: bool


class ItineraryDay(_Model):
    """derived itinerary_days.parquet: the default daily matching of the selected pairs
    (specs/002 research R2),
    with the day's scheduled layover when the flights connect."""

    itinerary_id: str
    service_date: dt.date
    match_status: Literal["connects", "not_connecting", "end_of_period"]
    sched_layover_min: int | None

    @model_validator(mode="after")
    def _layover(self) -> ItineraryDay:
        if (self.match_status == "connects") != (self.sched_layover_min is not None):
            raise ValueError("sched_layover_min is given exactly on connecting days")
        return self


class CurationMeta(_Model):
    """derived curation.json."""

    landing_comparison_id: str | None
    landing_reason: str
    airline_shares: dict[str, float]
    hub_shares: dict[str, float]
    cross_hub_share: Share
    shortfalls: list[str]


class AirlineCoverage(_Model):
    """Itineraries built through the selected hubs, and sampled DB1B passengers on sold
    same-airline routings through them, per marketing airline."""

    airline: Airline
    itineraries: NonNegInt
    sold_passengers: NonNegInt


class ShowcaseBreakdown(_Model):
    """Subsets of the showcase examples that the go/no-go decision cites (SC-010)."""

    examples: NonNegInt
    examples_per_pair: dict[str, int]
    cross_hub_examples: NonNegInt
    examples_without_tight_layover: NonNegInt
    pairs_without_tight_layover: NonNegInt
    hubs_without_tight_layover: list[str]
    nonstop_ratio_limit: float
    examples_slower_than_ratio: NonNegInt
    examples_without_nonstop: NonNegInt
    max_nonstop_ratio: float | None
    examples_missing_settings: dict[str, int]


class Finding(_Model):
    ontime_period_start: dt.date
    ontime_period_end: dt.date
    t100_period_start: dt.date
    t100_period_end: dt.date
    db1b_quarters: list[str]
    db1b_unknown_airline_share: Share
    db1b_unmapped_airlines: dict[str, int]
    db1b_unmapped_airline_share: Share
    showcase_breakdown: ShowcaseBreakdown | None
    airline_coverage: list[AirlineCoverage]
    od_exclusions: list[OdExclusions]
    hubs: list[HubSelection]
    unmet_constraints: list[str]
    od_pairs: list[OdSelection]
    od_pairs_without_itineraries: list[str]
    default_results: list[ItineraryResult]
    showcase_examples: list[ComparablePair]
    criterion_min_examples_met: bool
    criterion_min_hubs_met: bool
    decision: Decision
    ci_method: str
    limitations: list[str]
    data_quality: dict[str, int]

    @field_validator("hubs")
    @classmethod
    def _selected_only(cls, v: list[HubSelection]) -> list[HubSelection]:
        if any(not h.selected for h in v):
            raise ValueError("hubs lists selected hubs only")
        return v


# --- JSON side files (Principle IV: every output shape is a model) ---------------------


class QualitySummary(_Model):
    """reports/phase0/quality.json."""

    by_month: dict[str, dict[str, int]]
    totals: dict[str, int]
    clock_checked: NonNegInt
    clock_mismatch: NonNegInt
    clock_mismatch_share: Share
    clock_mismatch_max_share: Share
    sched_arr_mismatch: NonNegInt


class SoldRoutingsSummary(_Model):
    """derived sold_routings.json."""

    quarters: list[str]
    two_coupon_passengers: NonNegInt
    unknown_airline_passengers: NonNegInt
    unknown_airline_share: Share


class HubSelectionMeta(_Model):
    """derived hub_selection.json."""

    pool: list[str]
    selected: list[str]
    unmet_constraints: list[str]
    median_weather_share: Share


class OdSelectionMeta(_Model):
    """derived od_selection.json."""

    shortfalls: list[str]


class SensitivityMeta(_Model):
    """derived sensitivity.json."""

    pairs_without_itineraries: list[str]
    pair_scenarios_not_comparable: NonNegInt


class ScenarioSummary(_Model):
    """One row of derived sensitivity_summary.json."""

    scenario_id: str
    is_default: bool
    min_connection_min: NonNegInt
    boarding_cutoff_min: NonNegInt
    recurrence_threshold: Share
    itineraries: NonNegInt
    sufficient: NonNegInt
    median_rate: Share | None
    reversals: NonNegInt


class SourceRecord(_Model):
    """One acquired source file, as recorded in raw sources.json and the manifest."""

    name: str
    sha256: str
    pinned: bool
    path: str | None = None
    url: str | None = None


class Manifest(_Model):
    """reports/phase0/manifest.json."""

    config_sha256: str
    sources: list[SourceRecord]
    packages: dict[str, str]
    outputs: dict[str, str]
    run: dict[str, Any]


# --- Table validation --------------------------------------------------------------------


def _datetime_fields(model: type[BaseModel]) -> set[str]:
    out: set[str] = set()
    for name, info in model.model_fields.items():
        if "datetime" in repr(info.annotation).lower():
            out.add(name)
    return out


def _as_utc(value: Any) -> Any:
    if isinstance(value, dt.datetime) and value.tzinfo is None:
        return value.replace(tzinfo=dt.UTC)
    return value


def rows_as_dicts(columns: Sequence[str], rows: Iterable[tuple[Any, ...]]) -> list[dict[str, Any]]:
    return [dict(zip(columns, row, strict=True)) for row in rows]


def validate_table(
    con: duckdb.DuckDBPyConnection,
    source: str,
    model: type[BaseModel],
    *,
    batch_size: int = 100_000,
) -> int:
    """Validate every row of ``source`` (a table name, view or ``read_parquet(...)`` call)
    against ``model``. Column names must match the model's fields exactly. Returns the row
    count. Naive timestamps are read as UTC (storage convention)."""
    cur = con.execute(f"SELECT * FROM {source}")
    columns = [d[0] for d in cur.description or []]
    expected = list(model.model_fields)
    if set(columns) != set(expected):
        missing = sorted(set(expected) - set(columns))
        extra = sorted(set(columns) - set(expected))
        raise ValueError(
            f"{source} does not match {model.__name__}: missing {missing}, unexpected {extra}"
        )
    dt_fields = _datetime_fields(model)
    adapter: TypeAdapter[list[Any]] = TypeAdapter(list[model])  # pyright: ignore[reportInvalidTypeForm]
    total = 0
    while True:
        rows = cur.fetchmany(batch_size)
        if not rows:
            break
        records = rows_as_dicts(columns, rows)
        if dt_fields:
            for rec in records:
                for name in dt_fields:
                    rec[name] = _as_utc(rec[name])
        adapter.validate_python(records)
        total += len(records)
    return total
