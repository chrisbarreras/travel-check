"""Hub candidate metrics, eligibility, score and constrained selection (FR-006 to FR-012).

Selection procedure (data-model.md HubSelection): take the top ``count`` eligible candidates
by rank; then, for each unmet constraint in a fixed order (airline coverage per network, then
winter, summer, above-median, below-median weather), swap the lowest-ranked selected hub that
no constraint needs for the best-ranked eligible candidate that fixes it, until every
constraint holds or no swap helps. Unfixable constraints are reported.
"""

from __future__ import annotations

import statistics
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field

import duckdb

from flight_pipeline.config import SEASONS, Hubs
from flight_pipeline.models import Airport, HubCandidate, HubSelection, Season, SeasonShares

SCORE_DECIMALS = 6


@dataclass(frozen=True)
class CandidateMetrics:
    airport: str
    departures: int
    airlines: list[str]
    passengers: int | None
    weather_share: float
    weather_share_by_season: SeasonShares
    weather_peak_season: Season | str
    eligible_itineraries: int = 0


@dataclass(frozen=True)
class SelectionResult:
    candidates: list[HubCandidate]
    selection: list[HubSelection]
    unmet: list[str] = field(default_factory=list[str])
    median_weather_share: float = 0.0

    @property
    def selected(self) -> list[str]:
        return sorted(s.airport for s in self.selection if s.selected)


# --- Metrics (SQL) -----------------------------------------------------------------------

# Scheduled departures: distinct flight instances, so flagged duplicate copies count once.
_DEP_KEY = "marketing_airline, flight_number, service_date"


def candidate_pool(con: duckdb.DuckDBPyConnection, flights: str, size: int) -> list[str]:
    """The ``size`` airports with the most scheduled departures; ties by airport code."""
    rows = con.execute(
        f"""
        SELECT origin, count(DISTINCT ({_DEP_KEY})) AS deps FROM {flights}
        GROUP BY origin ORDER BY deps DESC, origin LIMIT {int(size)}
        """
    ).fetchall()
    return [r[0] for r in rows]


def _peak(shares: SeasonShares) -> Season | str:
    values = {s: getattr(shares, s) for s in SEASONS}
    known = {s: v for s, v in values.items() if v is not None}
    if not known:
        return "unknown"
    top = max(known.values())
    leaders = [s for s, v in known.items() if v == top]
    if top <= 0 or len(leaders) != 1:
        return "unknown"  # no weather-affected departures, or no single peak
    return leaders[0]


def candidate_metrics(
    con: duckdb.DuckDBPyConnection,
    flights: str,
    passengers: str,
    pool: Sequence[str],
    cfg: Hubs,
) -> list[CandidateMetrics]:
    """Airline count, departures, passengers and weather profile per candidate (FR-007).
    Eligibility is added separately (``count_eligible``)."""
    con.execute("CREATE OR REPLACE TEMP TABLE _pool (airport VARCHAR)")
    con.executemany("INSERT INTO _pool VALUES (?)", [(a,) for a in pool])
    season_case = " ".join(
        f"WHEN month(service_date) IN ({', '.join(map(str, months))}) THEN '{name}'"
        for name, months in zip(
            SEASONS,
            (cfg.winter_months, cfg.spring_months, cfg.summer_months, cfg.autumn_months),
            strict=True,
        )
    )
    con.execute(
        f"""
        CREATE OR REPLACE TEMP TABLE _deps AS
        SELECT DISTINCT origin, marketing_airline, flight_number, service_date,
               bool_or(weather_affected) OVER (
                   PARTITION BY origin, marketing_airline, flight_number, service_date
               ) AS weather,
               CASE {season_case} END AS season
        FROM {flights} WHERE origin IN (SELECT airport FROM _pool)
        """
    )
    totals = {
        r[0]: (int(r[1]), int(r[2]))
        for r in con.execute(
            "SELECT origin, count(*), count(*) FILTER (WHERE weather) FROM _deps GROUP BY 1"
        ).fetchall()
    }
    by_season: dict[str, dict[str, float]] = {}
    for origin, season, n, w in con.execute(
        "SELECT origin, season, count(*), count(*) FILTER (WHERE weather) FROM _deps GROUP BY 1, 2"
    ).fetchall():
        if int(w) > 0:  # no weather-affected departures in a season: unknown (spec)
            by_season.setdefault(origin, {})[season] = round(int(w) / int(n), SCORE_DECIMALS)
    airlines: dict[str, list[str]] = {}
    for origin, airline in con.execute(
        f"""
        SELECT origin, marketing_airline FROM (
            SELECT origin, marketing_airline, count(*) AS n,
                   sum(count(*)) OVER (PARTITION BY origin) AS total
            FROM _deps GROUP BY 1, 2
        ) WHERE n >= {cfg.airline_share_min} * total ORDER BY 1, 2
        """
    ).fetchall():
        airlines.setdefault(origin, []).append(airline)
    pax = {
        r[0]: int(r[1])
        for r in con.execute(
            f"SELECT origin, sum(passengers) FROM {passengers} "
            "WHERE origin IN (SELECT airport FROM _pool) GROUP BY 1"
        ).fetchall()
    }
    out: list[CandidateMetrics] = []
    for airport in pool:
        deps, weather = totals.get(airport, (0, 0))
        seasons = by_season.get(airport, {})
        shares = SeasonShares(**{s: seasons.get(s) for s in SEASONS})
        out.append(
            CandidateMetrics(
                airport=airport,
                departures=deps,
                airlines=airlines.get(airport, []),
                passengers=pax.get(airport),
                weather_share=weather / deps if deps else 0.0,
                weather_share_by_season=shares,
                weather_peak_season=_peak(shares),
            )
        )
    return out


def count_eligible(
    con: duckdb.DuckDBPyConnection, itineraries: str, pool: Sequence[str]
) -> dict[str, int]:
    """Qualifying itineraries through each candidate whose origin is outside the pool (FR-008)."""
    con.execute("CREATE OR REPLACE TEMP TABLE _pool_e (airport VARCHAR)")
    con.executemany("INSERT INTO _pool_e VALUES (?)", [(a,) for a in pool])
    rows = con.execute(
        f"""
        SELECT hub, count(*) FROM {itineraries}
        WHERE hub IN (SELECT airport FROM _pool_e)
          AND origin NOT IN (SELECT airport FROM _pool_e)
        GROUP BY hub
        """
    ).fetchall()
    counts = {a: 0 for a in pool}
    counts.update({r[0]: int(r[1]) for r in rows})
    return counts


# --- Score and selection (pure) ---------------------------------------------------------


def _scaled(values: list[float]) -> list[float]:
    lo, hi = min(values), max(values)
    if hi == lo:
        return [0.0 for _ in values]  # a component with no spread carries no information
    return [(v - lo) / (hi - lo) for v in values]


@dataclass
class _Constraint:
    name: str
    met: Callable[[set[str]], bool]
    fixes: Callable[[str], bool]
    needs: Callable[[set[str], str], bool]  # would removing this hub make it worse?
    label: Callable[[set[str]], str]


def select_hubs(metrics: Sequence[CandidateMetrics], cfg: Hubs) -> SelectionResult:
    ms = sorted(metrics, key=lambda m: m.airport)
    if not ms:
        return SelectionResult([], [], [f"hub_count (0 of {cfg.count}): no candidates"])
    weights = cfg.weights
    s_air = _scaled([float(len(m.airlines)) for m in ms])
    s_dep = _scaled([float(m.departures) for m in ms])
    s_pax = _scaled([float(m.passengers or 0) for m in ms])
    scores = {
        m.airport: round(
            weights.airlines * a + weights.departures * d + weights.passengers * p, SCORE_DECIMALS
        )
        for m, a, d, p in zip(ms, s_air, s_dep, s_pax, strict=True)
    }
    order = sorted(ms, key=lambda m: (-scores[m.airport], m.airport))
    rank = {m.airport: i + 1 for i, m in enumerate(order)}
    by_code = {m.airport: m for m in ms}
    eligible = {m.airport: m.eligible_itineraries >= cfg.eligible_itineraries_min for m in ms}
    median = statistics.median(m.weather_share for m in ms)

    def peak(a: str) -> str:
        return str(by_code[a].weather_peak_season)

    constraints: list[_Constraint] = []
    for net in cfg.major_networks:
        if not any(eligible[m.airport] and net in m.airlines for m in ms):
            continue  # no eligible candidate carries this network: nothing to require

        def covers(a: str, net: str = net) -> bool:
            return net in by_code[a].airlines

        constraints.append(
            _Constraint(
                name=f"airline_coverage:{net}",
                met=lambda sel, covers=covers: any(covers(a) for a in sel),
                fixes=covers,
                needs=lambda sel, a, covers=covers: covers(a) and sum(covers(x) for x in sel) <= 1,
                label=lambda sel, net=net: f"airline_coverage:{net}",
            )
        )
    for season, need in (("winter", cfg.min_winter_peak), ("summer", cfg.min_summer_peak)):
        if need <= 0:
            continue

        def is_season(a: str, season: str = season) -> bool:
            return peak(a) == season

        constraints.append(
            _Constraint(
                name=f"weather_{season}",
                met=lambda sel, f=is_season, n=need: sum(f(a) for a in sel) >= n,
                fixes=is_season,
                needs=lambda sel, a, f=is_season, n=need: f(a) and sum(f(x) for x in sel) <= n,
                label=lambda sel, f=is_season, n=need, s=season: (
                    f"weather_{s} ({sum(f(a) for a in sel)} of {n} hubs peak in {s})"
                ),
            )
        )

    def above(a: str) -> bool:
        return by_code[a].weather_share > median

    def below(a: str) -> bool:
        return by_code[a].weather_share < median

    sides: list[tuple[str, Callable[[str], bool]]] = [
        ("above_median", above),
        ("below_median", below),
    ]
    for side, test in sides:
        constraints.append(
            _Constraint(
                name=f"weather_{side}",
                met=lambda sel, t=test: any(t(a) for a in sel),
                fixes=test,
                needs=lambda sel, a, t=test: t(a) and sum(t(x) for x in sel) <= 1,
                label=lambda sel, s=side: f"weather_{s}",
            )
        )

    pool_eligible = [m.airport for m in order if eligible[m.airport]]
    selected: set[str] = set(pool_eligible[: cfg.count])
    reasons: dict[str, str] = {a: "score" for a in selected}
    unmet: list[str] = []
    if len(selected) < cfg.count:
        unmet.append(f"hub_count ({len(selected)} of {cfg.count}): too few eligible candidates")

    gave_up: set[str] = set()
    progress = True
    while progress:
        progress = False
        for c in constraints:
            if c.name in gave_up or c.met(selected):
                continue
            adds = [a for a in pool_eligible if a not in selected and c.fixes(a)]
            removable = [
                a
                for a in sorted(selected, key=lambda x: -rank[x])
                # needed by any constraint, met or not: removing it would make that worse
                if not any(k.needs(selected, a) for k in constraints) and not c.fixes(a)
            ]
            if not adds or not removable:
                gave_up.add(c.name)
                continue
            out, add = removable[0], adds[0]
            selected.discard(out)
            reasons.pop(out, None)
            selected.add(add)
            reasons[add] = c.name
            progress = True
            break
    for c in constraints:
        if not c.met(selected):
            unmet.append(c.label(selected))

    candidates = [
        HubCandidate(
            airport=m.airport,
            departures=m.departures,
            airline_count=len(m.airlines),
            airlines=list(m.airlines),
            passengers=m.passengers,
            weather_share=round(m.weather_share, SCORE_DECIMALS),
            weather_share_by_season=m.weather_share_by_season,
            weather_peak_season=m.weather_peak_season,  # type: ignore[arg-type]
            eligible_itineraries=m.eligible_itineraries,
            eligible=eligible[m.airport],
            score=scores[m.airport],
            rank=rank[m.airport],
        )
        for m in order
    ]
    selection = [
        HubSelection(
            airport=m.airport,
            selected=m.airport in selected,
            reason=reasons.get(m.airport) if m.airport in selected else None,
        )
        for m in order
    ]
    return SelectionResult(candidates, selection, unmet, median)


def assign_roles(
    codes: Sequence[str], tz: dict[str, str], pool: Sequence[str], selected: Sequence[str]
) -> list[Airport]:
    """Airport roles: selected ``hub``, other pool members ``candidate``, everything else
    ``regional`` (data-model.md Airport.role)."""
    pool_set, sel = set(pool), set(selected)
    out: list[Airport] = []
    for code in sorted(set(codes)):
        role = "hub" if code in sel else "candidate" if code in pool_set else "regional"
        out.append(Airport(code=code, tz=tz[code], role=role))
    return out
