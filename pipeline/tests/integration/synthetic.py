"""A deterministic synthetic year of BTS-format data for end-to-end tests.

Design (so the expected results follow from the design, not from the pipeline):

- 8 hubs (the candidate pool), 6 regional origins and 4 destinations outside the pool.
  Each airline flies each of its hubs daily: one inbound flight per origin, all leaving at
  14:00 UTC (written as local time at the origin), and one outbound flight per destination
  leaving 90 minutes after the inbound flights' scheduled arrival, and a second one 2 hours
  later (a 210-minute layover, within the 240-minute limit). Later outbound banks (5 to 15
  hours later, too late to connect) make the hubs the busiest airports, so they form the
  candidate pool. Block times are equal everywhere, so the itineraries of an
  origin/destination pair differ only in layover.
- Insights (specs/002 User Story 5): at a weather hub the later outbound absorbs most
  inbound delays, so it is a better connecting option for the 90-minute connection; at a
  reliable hub the 90-minute connection is a faster alternative, 2 hours shorter and as
  reliable, to the 210-minute one.
- Weather at ORD and MSP in winter, ATL and PHX in summer, rare elsewhere. On a weather day
  an inbound flight to the hub is 80-180 minutes late (so the connection fails at every
  sensitivity threshold, 35-65 minutes), and a departure from the hub is 15 minutes late with
  weather as the cause (so the hub's weather profile peaks in that season). Otherwise flights
  are within 5 minutes of schedule and every connection is feasible. Itinerary order
  therefore never reverses across scenarios.
- AS flies only SEA, so airline coverage forces SEA into the selection.
- DB1B: every connecting routing is sold, 10 sampled passengers per quarter (40 over the
  period, above the minimum of 30), except UA through DEN to BOS (5 per quarter, 20 in all),
  which is excluded as not sold. A few legs have no recorded selling airline.
- The period is July 2024 to June 2025, the configured period.
- Scheduled times are fixed local times all year, as airlines publish them (their summer
  value), so UTC times move with daylight saving. Phoenix keeps no daylight saving: there
  the first bank's layover is 30 minutes from November to March (tight, mostly failing),
  and the second bank does not connect then.
- Phase 1 (specs/002): WN flies the same schedules under alternating flight numbers (odd and
  even days), so only schedule-slot identity sees its itineraries; DL flies nonstops from CMH
  and TUL to every destination; and on AA's hubs CMH has a second inbound bank, 60 minutes
  later, so CMH routes have more itineraries and dominate the showcase unless curation caps
  them. The second bank's layover is the 30-minute minimum, so its connections are tight and
  mostly fail. Six outbound banks (the first two connect) keep the hubs the busiest
  airports, so the candidate pool is still the 8 hubs.
"""

from __future__ import annotations

import csv
import datetime as dt
import random
import zipfile
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from tests.fixtures import make_db1b_sample as db1b
from tests.fixtures import make_ontime_sample as fmt

HUB_TZ = {
    "ORD": "America/Chicago",
    "DFW": "America/Chicago",
    "ATL": "America/New_York",
    "DEN": "America/Denver",
    "SEA": "America/Los_Angeles",
    "PHX": "America/Phoenix",
    "MSP": "America/Chicago",
    "CLT": "America/New_York",
}
ORIGINS = {
    "CMH": "America/New_York",
    "BOI": "America/Boise",
    "TUL": "America/Chicago",
    "DSM": "America/Chicago",
    "ICT": "America/Chicago",
    "OMA": "America/Chicago",
}
DESTS = {
    "SAN": "America/Los_Angeles",
    "BOS": "America/New_York",
    "MIA": "America/New_York",
    "LAS": "America/Los_Angeles",
}
AIRLINE_HUBS = {
    "AA": ["DFW", "ORD", "CLT", "PHX"],
    "DL": ["ATL", "MSP", "SEA"],
    "UA": ["ORD", "DEN"],
    "WN": ["DEN", "PHX"],
    "AS": ["SEA"],
}
WINTER_PEAK = ("ORD", "MSP")
SUMMER_PEAK = ("ATL", "PHX")
START = dt.date(2024, 7, 1)
QUARTERS = ((2024, 3), (2024, 4), (2025, 1), (2025, 2))
UNSOLD = ("UA", "DEN", "BOS")  # sold below the minimum
DAYS = 365
IN_BLOCK, OUT_BLOCK, LAYOVER = 100, 150, 90
BANK_OFFSETS_MIN = (0, 120, 300, 480, 660, 900)  # the first two connect (max 240)
NONSTOP_ORIGINS = ("CMH", "TUL")
NONSTOP_BLOCK = 200
SECOND_BANK = {"CMH": 60}  # an extra inbound leaving this many minutes after the first
SECOND_BANK_AIRLINE = "AA"  # only on this airline's hubs, so origins stay smaller than hubs
RENUMBERING = "WN"  # flies the same schedules under alternating flight numbers


def renumber(airline: str, number: int, day_index: int) -> int:
    """The flight number flown on a given day: fixed, except for the renumbering airline,
    which adds 5000 on odd days (only schedule-slot identity sees it as one flight)."""
    return number + 5000 if airline == RENUMBERING and day_index % 2 == 1 else number


def weather_probability(hub: str, month: int) -> float:
    if hub in WINTER_PEAK:
        return 0.45 if month in (12, 1, 2) else 0.06
    if hub in SUMMER_PEAK:
        return 0.40 if month in (6, 7, 8) else 0.06
    return 0.02


def _hhmm(instant: dt.datetime, tz: str) -> str:
    """The scheduled local time, fixed all year as in airline schedules: the local time of
    the instant's UTC time of day on the period's first day (summer time)."""
    ref = dt.datetime.combine(START, instant.timetz())
    t = ref.astimezone(ZoneInfo(tz))
    return f"{t.hour:02d}{t.minute:02d}"


def write_year(raw_dir: Path, seed: int = 7) -> None:
    """Write raw_dir/ontime/YYYY-MM.csv (12 months), raw_dir/db1b/YYYY-Q.zip (4 quarters)
    and raw_dir/t100/t100_segment.csv."""
    fmt.TZ.update(HUB_TZ | ORIGINS | DESTS)
    rng = random.Random(seed)
    numbers: dict[tuple[str, str, str], int] = {}
    n = 1000
    for airline, hubs in sorted(AIRLINE_HUBS.items()):
        for hub in hubs:
            for origin in sorted(ORIGINS):
                n += 1
                numbers[(airline, hub, origin)] = n
                if origin in SECOND_BANK and airline == SECOND_BANK_AIRLINE:
                    n += 1
                    numbers[(airline, hub, origin + "2")] = n
            for dest in sorted(DESTS):
                for bank in range(len(BANK_OFFSETS_MIN)):
                    n += 1
                    numbers[(airline, hub, f"{dest}{bank}")] = n
    rows: dict[str, list[list[str]]] = {}
    for i in range(DAYS):
        day = START + dt.timedelta(days=i)
        key = f"{day.year:04d}-{day.month:02d}"
        dep_utc = dt.datetime.combine(day, dt.time(14, 0), tzinfo=dt.UTC)
        out_utc = dep_utc + dt.timedelta(minutes=IN_BLOCK + LAYOVER)
        for airline, hubs in sorted(AIRLINE_HUBS.items()):
            for hub in hubs:
                p = weather_probability(hub, day.month)
                for origin, tz in sorted(ORIGINS.items()):
                    banks = [(origin, dep_utc)]
                    if origin in SECOND_BANK and airline == SECOND_BANK_AIRLINE:
                        later = dep_utc + dt.timedelta(minutes=SECOND_BANK[origin])
                        banks.append((origin + "2", later))
                    for bank_key, dep in banks:
                        num = renumber(airline, numbers[(airline, hub, bank_key)], i)
                        crs = _hhmm(dep, tz)
                        roll = rng.random()
                        if roll < 0.004:
                            kw: dict[str, Any] = {
                                "cancelled": True,
                                "code": "A",
                                "dep_delay": None,
                            }
                        elif roll < 0.004 + p:
                            late = rng.randint(80, 180)
                            kw = {"dep_delay": late, "weather": late}
                        else:
                            kw = {"dep_delay": rng.randint(-5, 5)}
                        row = fmt.Row(
                            "synthetic",
                            day,
                            airline,
                            num,
                            airline,
                            origin,
                            hub,
                            crs,
                            IN_BLOCK,
                            **kw,
                        )
                        rows.setdefault(key, []).append(fmt.render(row))
                for dest in sorted(DESTS):
                    for bank, offset in enumerate(BANK_OFFSETS_MIN):
                        num = renumber(airline, numbers[(airline, hub, f"{dest}{bank}")], i)
                        crs = _hhmm(out_utc + dt.timedelta(minutes=offset), HUB_TZ[hub])
                        if rng.random() < p:
                            kw = {"dep_delay": 15, "weather": 15}
                        else:
                            kw = {"dep_delay": rng.randint(-3, 5)}
                        row = fmt.Row(
                            "synthetic", day, airline, num, airline, hub, dest, crs, OUT_BLOCK, **kw
                        )
                        rows.setdefault(key, []).append(fmt.render(row))
        # DL nonstops from CMH and TUL to every destination, 08:00 local
        for k, origin in enumerate(NONSTOP_ORIGINS):
            for j, dest in enumerate(sorted(DESTS)):
                row = fmt.Row(
                    "synthetic",
                    day,
                    "DL",
                    9000 + 10 * k + j,
                    "DL",
                    origin,
                    dest,
                    "0800",
                    NONSTOP_BLOCK,
                    dep_delay=rng.randint(-5, 5),
                )
                rows.setdefault(key, []).append(fmt.render(row))
    ontime = raw_dir / "ontime"
    ontime.mkdir(parents=True, exist_ok=True)
    for key, month_rows in rows.items():
        with (ontime / f"{key}.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f, lineterminator="\n")
            w.writerow(fmt.HEADER)
            w.writerows(month_rows)
    t100 = raw_dir / "t100"
    t100.mkdir(parents=True, exist_ok=True)
    with (t100 / "t100_segment.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["PASSENGERS", "UNIQUE_CARRIER", "ORIGIN", "YEAR", "MONTH"])
        months = [(2024, m) for m in range(7, 13)] + [(2025, m) for m in range(1, 7)]
        for year, month in months:
            for airline, hubs in sorted(AIRLINE_HUBS.items()):
                for hub in hubs:
                    w.writerow([f"{5000 + 100 * len(hubs)}.00", airline, hub, year, month])
    write_db1b(raw_dir)


def write_db1b(raw_dir: Path) -> None:
    out = raw_dir / "db1b"
    out.mkdir(parents=True, exist_ok=True)
    i = 0
    for year, quarter in QUARTERS:
        lines = [",".join(db1b.HEADER)]
        for airline, hubs in sorted(AIRLINE_HUBS.items()):
            for hub in hubs:
                for origin in sorted(ORIGINS):
                    for dest in sorted(DESTS):
                        pax = 5 if (airline, hub, dest) == UNSOLD else 10
                        row = (
                            "synthetic",
                            year,
                            quarter,
                            2,
                            f"{origin}:{hub}:{dest}",
                            f"{airline}:{airline}",
                            pax,
                        )
                        i += 1
                        lines.append(",".join(db1b.render(i, row)))
        i += 1
        unknown = ("unknown", year, quarter, 2, "CMH:ORD:SAN", "AA:--", 3)
        lines.append(",".join(db1b.render(i, unknown)))
        with zipfile.ZipFile(out / f"{year}-{quarter}.zip", "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr(f"Market_{year}_{quarter}.csv", "\n".join(lines) + "\n")
