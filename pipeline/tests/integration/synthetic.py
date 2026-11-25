"""A deterministic synthetic year of BTS-format data for end-to-end tests.

Design (so the expected results follow from the design, not from the pipeline):

- 8 hubs (the candidate pool), 6 regional origins and 4 destinations outside the pool.
  Each airline flies each of its hubs daily: one inbound flight per origin, all leaving at
  14:00 UTC (written as local time at the origin), and one outbound flight per destination
  leaving 90 minutes after the inbound flights' scheduled arrival. Three later outbound banks
  (5, 8 and 11 hours later, too late to connect) make the hubs the busiest airports, so they
  form the candidate pool. Block times are equal everywhere, so every itinerary of an
  origin/destination pair is comparable.
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
BANK_OFFSETS_MIN = (0, 300, 480, 660)  # only the first bank connects (max layover 240)


def weather_probability(hub: str, month: int) -> float:
    if hub in WINTER_PEAK:
        return 0.45 if month in (12, 1, 2) else 0.06
    if hub in SUMMER_PEAK:
        return 0.40 if month in (6, 7, 8) else 0.06
    return 0.02


def _hhmm(instant: dt.datetime, tz: str) -> str:
    t = instant.astimezone(ZoneInfo(tz))
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
                    num = numbers[(airline, hub, origin)]
                    crs = _hhmm(dep_utc, tz)
                    roll = rng.random()
                    if roll < 0.004:
                        kw: dict[str, Any] = {"cancelled": True, "code": "A", "dep_delay": None}
                    elif roll < 0.004 + p:
                        late = rng.randint(80, 180)
                        kw = {"dep_delay": late, "weather": late}
                    else:
                        kw = {"dep_delay": rng.randint(-5, 5)}
                    row = fmt.Row(
                        "synthetic", day, airline, num, airline, origin, hub, crs, IN_BLOCK, **kw
                    )
                    rows.setdefault(key, []).append(fmt.render(row))
                for dest in sorted(DESTS):
                    for bank, offset in enumerate(BANK_OFFSETS_MIN):
                        num = numbers[(airline, hub, f"{dest}{bank}")]
                        crs = _hhmm(out_utc + dt.timedelta(minutes=offset), HUB_TZ[hub])
                        if rng.random() < p:
                            kw = {"dep_delay": 15, "weather": 15}
                        else:
                            kw = {"dep_delay": rng.randint(-3, 5)}
                        row = fmt.Row(
                            "synthetic", day, airline, num, airline, hub, dest, crs, OUT_BLOCK, **kw
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
