"""Generate ontime_sample.csv in the real BTS Marketing Carrier format.

Run from pipeline/: ``uv run python tests/fixtures/make_ontime_sample.py``. The CSV is
committed; this script documents exactly how each row was built. Derived clock fields
(CRSArrTime, DepTime, ArrTime, ArrDelay) are computed here with zoneinfo directly, which is
independent of the pipeline's own conversion code. Expected results are written by hand in
expected/*.json, not computed by this script. See README.md for the case list.
"""

from __future__ import annotations

import csv
import datetime as dt
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

TZ = {
    "CMH": "America/New_York",
    "ORD": "America/Chicago",
    "SAN": "America/Los_Angeles",
    "SEA": "America/Los_Angeles",
    "DEN": "America/Denver",
    "PHX": "America/Phoenix",
}

# Real header order (subset of the 120 BTS columns, plus extras the pipeline must ignore).
HEADER = [
    "Year",
    "FlightDate",
    "Marketing_Airline_Network",
    "Flight_Number_Marketing_Airline",
    "Operating_Airline ",  # trailing space, as in the real files
    "Tail_Number",
    "Origin",
    "Dest",
    "CRSDepTime",
    "DepTime",
    "DepDelay",
    "CRSArrTime",
    "ArrTime",
    "ArrDelay",
    "Cancelled",
    "CancellationCode",
    "Diverted",
    "CRSElapsedTime",
    "ActualElapsedTime",
    "WeatherDelay",
    "NASDelay",
    "Duplicate",
    "FixtureCase",
    "",  # real files end every line with a trailing comma
]


@dataclass
class Row:
    case: str
    date: dt.date
    mkt: str
    num: int
    op: str
    orig: str
    dest: str
    crs_dep: str  # HHMM local at origin
    crs_elapsed: int
    dep_delay: int | None = 0
    act_elapsed: int | None = None  # defaults to crs_elapsed when operated
    cancelled: bool = False
    code: str = ""
    diverted: bool = False
    weather: int | None = None
    nas: int | None = None
    arr_time_override: str | None = None  # to create a clock-time mismatch


def hhmm_to_min(s: str) -> int:
    v = int(s)
    return (v // 100) * 60 + v % 100


def clock(minutes: int, *, actual: bool) -> str:
    m = minutes % 1440
    if m == 0 and actual:
        return "2400"  # BTS writes actual midnight as 2400
    return f"{m // 60:02d}{m % 60:02d}"


def sched_dep_utc(r: Row) -> dt.datetime:
    local = dt.datetime.combine(r.date, dt.time()) + dt.timedelta(minutes=hhmm_to_min(r.crs_dep))
    return local.replace(tzinfo=ZoneInfo(TZ[r.orig])).astimezone(dt.UTC)


def local_min(instant: dt.datetime, airport: str) -> int:
    t = instant.astimezone(ZoneInfo(TZ[airport]))
    return t.hour * 60 + t.minute


def f2(v: int | None) -> str:
    return "" if v is None else f"{v}.00"


def render(r: Row) -> list[str]:
    sdep = sched_dep_utc(r)
    sarr = sdep + dt.timedelta(minutes=r.crs_elapsed)
    operated = not r.cancelled
    dep_time = dep_delay = arr_time = arr_delay = act_el = ""
    if operated and r.dep_delay is not None:
        dep_delay = f2(r.dep_delay)
        dep_time = clock(hhmm_to_min(r.crs_dep) + r.dep_delay, actual=True)
        if not r.diverted:
            el = r.crs_elapsed if r.act_elapsed is None else r.act_elapsed
            act_el = f2(el)
            aarr = sdep + dt.timedelta(minutes=r.dep_delay + el)
            arr_time = r.arr_time_override or clock(local_min(aarr, r.dest), actual=True)
            arr_delay = f2(int((aarr - sarr).total_seconds() // 60))
    return [
        str(r.date.year),
        r.date.isoformat(),
        r.mkt,
        str(r.num),
        r.op,
        "N123XX",
        r.orig,
        r.dest,
        r.crs_dep,
        dep_time,
        dep_delay,
        clock(local_min(sarr, r.dest), actual=False),
        arr_time,
        arr_delay,
        "1.00" if r.cancelled else "0.00",
        r.code,
        "1.00" if r.diverted else "0.00",
        f2(r.crs_elapsed),
        act_el,
        f2(r.weather),
        f2(r.nas),
        "N",
        r.case,
        "",
    ]


JAN = [dt.date(2026, 1, 5) + dt.timedelta(days=i) for i in range(10)]  # d1..d10


def rows() -> list[Row]:
    out: list[Row] = []

    # Itinerary 1: AA3100 CMH->ORD (operated by MQ) + AA1500 ORD->SAN. Daily cases d1..d10.
    inbound: dict[int, dict[str, Any]] = {
        1: {},
        2: {"dep_delay": 50, "nas": 50},  # NAS delay only: not weather-affected
        3: {"dep_delay": 40, "act_elapsed": 85, "nas": 45},
        4: {"cancelled": True, "code": "B", "dep_delay": None},  # weather cancellation
        5: {},
        6: {"dep_delay": 10, "diverted": True},
        7: {"dep_delay": None},  # operated, actual times missing
        8: {"dep_delay": 120, "weather": 120},  # weather delay
        9: {},
        10: {},
    }
    for d, kw in inbound.items():
        out.append(Row(f"i1_in_d{d}", JAN[d - 1], "AA", 3100, "MQ", "CMH", "ORD", "0800", 80, **kw))
    # d10: a second, conflicting copy of the inbound record (different delay)
    out.append(
        Row("i1_in_d10_conflict", JAN[9], "AA", 3100, "MQ", "CMH", "ORD", "0800", 80, dep_delay=30)
    )
    outbound = {
        1: {"dep_delay": 5},
        5: {"cancelled": True, "code": "A", "dep_delay": None},
        8: {"dep_delay": 2},
    }
    for d in range(1, 11):
        out.append(
            Row(
                f"i1_out_d{d}",
                JAN[d - 1],
                "AA",
                1500,
                "AA",
                "ORD",
                "SAN",
                "0950",
                270,
                **outbound.get(d, {}),
            )
        )
    # d9: an identical duplicate of the outbound record
    out.append(Row("i1_out_d9", JAN[8], "AA", 1500, "AA", "ORD", "SAN", "0950", 270))

    # Partner AS outbounds: 70 min layover (included) and 40 min (below the 45 min partner minimum)
    for d in range(1, 11):
        out.append(Row(f"as700_d{d}", JAN[d - 1], "AS", 700, "AS", "ORD", "SEA", "0930", 270))
        out.append(Row(f"as702_d{d}", JAN[d - 1], "AS", 702, "AS", "ORD", "SEA", "0900", 270))
    # Same-airline layover limits: 20 min (too short), 250 min (too long), 240 min (boundary)
    for num, dep in ((1502, "0840"), (1504, "1230"), (1506, "1220")):
        for d in range(1, 11):
            out.append(Row(f"aa{num}_d{d}", JAN[d - 1], "AA", num, "AA", "ORD", "SAN", dep, 270))
    # Recurrence: AA1508 on 5/10 days (excluded at 60%); AA1510 on 6/10 days, 2 cancelled
    for d in range(1, 6):
        out.append(Row(f"aa1508_d{d}", JAN[d - 1], "AA", 1508, "AA", "ORD", "DEN", "1000", 150))
    for d in range(1, 7):
        kw: dict[str, Any] = (
            {"cancelled": True, "code": "A", "dep_delay": None} if d in (2, 3) else {}
        )
        out.append(
            Row(f"aa1510_d{d}", JAN[d - 1], "AA", 1510, "AA", "ORD", "DEN", "1030", 150, **kw)
        )
    # Same regional operator (OO), different marketing airlines (DL, UA), not partners
    for d in range(1, 11):
        out.append(Row(f"dl5000_d{d}", JAN[d - 1], "DL", 5000, "OO", "CMH", "ORD", "0700", 80))
        out.append(Row(f"ua6000_d{d}", JAN[d - 1], "UA", 6000, "OO", "ORD", "SAN", "0830", 270))

    # Connection-level recurrence: UA7000 CMH->ORD and UA7001 ORD->DEN both fly every day, but
    # they connect only on odd days (60 min layover); on even days UA7001 leaves 310 min after
    # the arrival, outside the 240 min maximum. Connect share 5/10 = 50% < 60% (amendment 1).
    for d in range(1, 11):
        out.append(Row(f"ua7000_d{d}", JAN[d - 1], "UA", 7000, "UA", "CMH", "ORD", "0900", 80))
        dep = "1020" if d % 2 == 1 else "1430"
        out.append(Row(f"ua7001_d{d}", JAN[d - 1], "UA", 7001, "UA", "ORD", "DEN", dep, 120))

    # Schedule changes: UA7002 CMH->ORD arrives 08:20 CT on d1-d6 and 09:20 CT on d7-d10;
    # UA7003 ORD->DEN leaves 09:00 CT on d1-d4 and 10:00 CT on d5-d10. Daily layovers are
    # 40, 40, 40, 40, 100, 100, 40, 40, 40, 40 (median 40, tight), but the separate pattern
    # medians (08:20 and 10:00) give 100. With UA7000 (09:20 CT), UA7003 connects only on
    # d5-d10 (40 min; 6 of 10 days).
    for d in range(1, 11):
        dep_in = "0800" if d <= 6 else "0900"
        out.append(Row(f"ua7002_d{d}", JAN[d - 1], "UA", 7002, "UA", "CMH", "ORD", dep_in, 80))
        dep_out = "0900" if d <= 4 else "1000"
        out.append(Row(f"ua7003_d{d}", JAN[d - 1], "UA", 7003, "UA", "ORD", "DEN", dep_out, 120))

    # Midnight itinerary: AA2200 CMH->ORD 22:00 ET + AA2300 ORD->PHX 00:30 CT next day
    for d in range(1, 11):
        kw: dict[str, Any] = (
            {"dep_delay": 95} if d == 2 else {}
        )  # d2: arrives just after local midnight
        out.append(
            Row(f"aa2200_d{d}", JAN[d - 1], "AA", 2200, "AA", "CMH", "ORD", "2200", 85, **kw)
        )
        out.append(Row(f"aa2300_d{d}", JAN[d - 1], "AA", 2300, "AA", "ORD", "PHX", "0030", 190))

    # Daylight-saving changes (time conversion and slack only; WN, not recurring)
    spring = dt.date(2026, 3, 8)
    fall = dt.date(2025, 11, 2)
    out.append(Row("dst_spring_in", spring, "WN", 101, "WN", "CMH", "ORD", "0130", 80))
    out.append(Row("dst_spring_out", spring, "WN", 102, "WN", "ORD", "DEN", "0320", 120))
    out.append(Row("dst_fall_in", fall, "WN", 201, "WN", "CMH", "ORD", "0030", 80))
    out.append(Row("dst_fall_out", fall, "WN", 202, "WN", "ORD", "DEN", "0210", 120))
    # 2400 and 0000 scheduled departures (same instant)
    out.append(Row("t2400", dt.date(2026, 1, 7), "WN", 301, "WN", "PHX", "SAN", "2400", 75))
    out.append(Row("t0000", dt.date(2026, 1, 8), "WN", 302, "WN", "PHX", "SAN", "0000", 75))
    # One flight number, two segments on the same day (CMH-ORD then ORD-DEN): distinct flights
    seg_day = dt.date(2026, 1, 10)
    out.append(Row("seg_1", seg_day, "WN", 501, "WN", "CMH", "ORD", "0700", 80))
    out.append(Row("seg_2", seg_day, "WN", 501, "WN", "ORD", "DEN", "0820", 120))
    # Clock-time mismatch: ArrTime 15 minutes off the computed arrival
    out.append(
        Row(
            "clock_mismatch",
            dt.date(2026, 1, 9),
            "WN",
            401,
            "WN",
            "CMH",
            "ORD",
            "1200",
            80,
            arr_time_override="1235",
        )
    )
    return out


def main() -> None:
    path = Path(__file__).parent / "ontime_sample.csv"
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(HEADER)
        for r in rows():
            w.writerow(render(r))
    print(f"wrote {path}")


if __name__ == "__main__":
    main()
