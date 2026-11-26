"""Schedule slots: itinerary identity by schedule, not flight number (ADR-0014, research R1).

For each marketing airline, origin and destination, every flight-day in the period is
assigned to exactly one slot:

1. scheduled local departure minutes are clustered, a new cluster starting wherever the gap
   to the previous minute exceeds the window; a cluster wider than twice the window is split
   at its largest gap;
2. a cluster with several flights on some day is split into ranked sub-slots (the k flights
   of a k-flight day, ordered by time and flight number); flights on other days go to a free
   sub-slot carrying their flight number, else the nearest reference time, else the lowest
   rank;
3. sub-slots that follow each other (the later starting at most 7 days after the earlier
   ends) and share a flight number across the boundary are joined: a schedule change, not a
   new flight.

Local time of day is used because it stays stable across daylight-saving changes; every
measured quantity elsewhere stays in UTC (ADR-0008, plan Complexity Tracking).
"""

from __future__ import annotations

import csv
import datetime as dt
import itertools
import tempfile
from collections import Counter
from collections.abc import Iterator, Sequence
from dataclasses import dataclass, field
from pathlib import Path

import duckdb

JOIN_MAX_GAP_DAYS = 7
_SLOT_COLUMNS = (
    "'slot_id': 'VARCHAR', "
    "'marketing_airline': 'VARCHAR', "
    "'origin': 'VARCHAR', "
    "'dest': 'VARCHAR', "
    "'ref': 'INTEGER', "
    "'lo': 'INTEGER', "
    "'hi': 'INTEGER', "
    "'days': 'INTEGER', "
    "'numbers': 'VARCHAR'"
)
_DAY_COLUMNS = (
    "'slot_id': 'VARCHAR', "
    "'service_date': 'DATE', "
    "'marketing_airline': 'VARCHAR', "
    "'flight_number': 'INTEGER', "
    "'origin': 'VARCHAR', "
    "'dest': 'VARCHAR', "
    "'dep_local_min': 'INTEGER'"
)
_CHANGE_COLUMNS = (
    "'slot_id': 'VARCHAR', "
    "'change_date': 'DATE', "
    "'from_local_min': 'INTEGER', "
    "'to_local_min': 'INTEGER'"
)


@dataclass(frozen=True, order=True)
class SlotRecord:
    """One flight-day: its date, scheduled local departure minute and flight number."""

    date: dt.date
    dep_local_min: int
    flight_number: str


@dataclass
class GroupSlot:
    """A slot within one airline/origin/destination group."""

    records: list[SlotRecord]
    changes: list[tuple[dt.date, int, int]] = field(
        default_factory=lambda: list[tuple[dt.date, int, int]]()
    )

    @property
    def ref_dep_local_min(self) -> int:
        times = sorted(r.dep_local_min for r in self.records)
        return times[(len(times) - 1) // 2]  # lower median, as quantile_disc elsewhere

    @property
    def first(self) -> SlotRecord:
        return min(self.records)

    @property
    def last(self) -> SlotRecord:
        return max(self.records)


def _clusters(times: Sequence[int], window: int) -> list[list[int]]:
    """Distinct sorted minutes grouped by gaps larger than the window; clusters wider than
    twice the window split at their largest gap (ties: the gap nearest the middle, then
    the earliest)."""
    distinct = sorted(set(times))
    groups: list[list[int]] = []
    for t in distinct:
        if groups and t - groups[-1][-1] <= window:
            groups[-1].append(t)
        else:
            groups.append([t])
    out: list[list[int]] = []
    stack = groups[::-1]
    while stack:
        g = stack.pop()
        if g[-1] - g[0] <= 2 * window or len(g) < 2:
            out.append(g)
            continue
        gaps = [(g[i + 1] - g[i], i) for i in range(len(g) - 1)]
        mid = (g[0] + g[-1]) / 2
        _, cut = max(gaps, key=lambda x: (x[0], -abs((g[x[1]] + g[x[1] + 1]) / 2 - mid), -x[1]))
        stack.extend([g[cut + 1 :], g[: cut + 1]])
    return sorted(out)


def _split_by_rank(records: list[SlotRecord]) -> list[GroupSlot]:
    by_day: dict[dt.date, list[SlotRecord]] = {}
    for r in sorted(records, key=lambda r: (r.date, r.dep_local_min, r.flight_number)):
        by_day.setdefault(r.date, []).append(r)
    k = max(len(v) for v in by_day.values())
    if k == 1:
        return [GroupSlot(sorted(records))]
    full_days = [v for v in by_day.values() if len(v) == k]
    refs: list[int] = []
    numbers: list[set[str]] = []
    for rank in range(k):
        times = sorted(day[rank].dep_local_min for day in full_days)
        refs.append(times[(len(times) - 1) // 2])
        numbers.append({day[rank].flight_number for day in full_days})
    subs: list[list[SlotRecord]] = [[] for _ in range(k)]
    for day in by_day.values():
        if len(day) == k:
            for rank, r in enumerate(day):
                subs[rank].append(r)
            continue
        free = set(range(k))
        for r in day:
            own = [i for i in sorted(free) if r.flight_number in numbers[i]]
            pick = (
                own[0]
                if own
                else min(sorted(free), key=lambda i: (abs(r.dep_local_min - refs[i]), i))
            )
            subs[pick].append(r)
            free.discard(pick)
    return [GroupSlot(sorted(s)) for s in subs if s]


def _runs(records: Sequence[SlotRecord]) -> list[list[SlotRecord]]:
    """Records split wherever consecutive days are more than the join gap apart."""
    out: list[list[SlotRecord]] = []
    for r in sorted(records):
        if out and (r.date - out[-1][-1].date).days <= JOIN_MAX_GAP_DAYS:
            out[-1].append(r)
        else:
            out.append([r])
    return out


def _join(slots: list[GroupSlot]) -> list[GroupSlot]:
    """Join sub-slots across schedule changes. Each sub-slot is cut into runs (no gap longer
    than the join gap); a run joins the run that starts at most the join gap after it ends
    and carries the same flight number across the boundary, so a change and a change back
    (A, B, A) is one slot. Runs of one sub-slot always stay together, and a join is made
    only when the two slots never fly on the same day."""
    parent = list(range(len(slots)))
    dates = [{r.date for r in s.records} for s in slots]
    changes: list[list[tuple[dt.date, int, int]]] = [list(s.changes) for s in slots]

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    pieces = sorted(
        ((run, i) for i, s in enumerate(slots) for run in _runs(s.records)),
        key=lambda p: (p[0][0].date, slots[p[1]].ref_dep_local_min, p[0][0].flight_number),
    )
    has_successor: set[int] = set()
    has_predecessor: set[int] = set()
    for ai, (a_run, a) in enumerate(pieces):
        last = a_run[-1]
        candidates = [
            (bi, b_run, b)
            for bi, (b_run, b) in enumerate(pieces)
            if bi not in has_predecessor
            and b != a  # runs of one sub-slot belong together already
            and last.date < b_run[0].date <= last.date + dt.timedelta(days=JOIN_MAX_GAP_DAYS)
            and b_run[0].flight_number == last.flight_number
        ]
        if not candidates or ai in has_successor:
            continue
        bi, b_run, b = min(
            candidates,
            key=lambda c: (
                c[1][0].date,
                abs(slots[c[2]].ref_dep_local_min - slots[a].ref_dep_local_min),
            ),
        )
        ra, rb = find(a), find(b)
        change = (b_run[0].date, last.dep_local_min, b_run[0].dep_local_min)
        if ra != rb:
            if dates[ra] & dates[rb]:
                continue
            parent[rb] = ra
            dates[ra] |= dates[rb]
            changes[ra] += changes[rb]
        changes[ra].append(change)  # also the change back into a slot already joined (A, B, A)
        has_successor.add(ai)
        has_predecessor.add(bi)
    groups: dict[int, list[SlotRecord]] = {}
    for i, s in enumerate(slots):
        groups.setdefault(find(i), []).extend(s.records)
    return [GroupSlot(sorted(recs), sorted(changes[root])) for root, recs in groups.items()]


def assign_slots(records: Sequence[SlotRecord], window_min: int) -> list[GroupSlot]:
    """Slots of one airline/origin/destination group (research R1), sorted by reference time
    and first date. Each record must be a distinct flight-day."""
    if not records:
        return []
    subs: list[GroupSlot] = []
    for cluster in _clusters([r.dep_local_min for r in records], window_min):
        members = set(cluster)
        subs.extend(_split_by_rank([r for r in records if r.dep_local_min in members]))
    joined = _join(subs)
    return sorted(joined, key=lambda s: (s.ref_dep_local_min, s.first.date, s.first.flight_number))


def _hhmm(minute: int) -> str:
    return f"{minute // 60:02d}{minute % 60:02d}"


def _groups(
    con: duckdb.DuckDBPyConnection, flights: str, period: tuple[dt.date, dt.date]
) -> Iterator[tuple[tuple[str, str, str], list[SlotRecord]]]:
    start, end = period
    cur = con.execute(
        f"""
        SELECT marketing_airline, origin, dest, service_date,
               min(sched_dep_local_min) AS dep, marketing_airline || CAST(flight_number AS VARCHAR)
        FROM {flights}
        WHERE service_date BETWEEN DATE '{start}' AND DATE '{end}'
        GROUP BY marketing_airline, flight_number, origin, dest, service_date
        ORDER BY 1, 2, 3, 4, 5, 6
        """
    )

    def rows() -> Iterator[tuple[str, str, str, dt.date, int, str]]:
        while batch := cur.fetchmany(200_000):
            yield from batch

    for key, group in itertools.groupby(rows(), key=lambda r: (r[0], r[1], r[2])):
        yield key, [SlotRecord(r[3], int(r[4]), r[5]) for r in group]


def build_slots(
    con: duckdb.DuckDBPyConnection,
    flights: str,
    period: tuple[dt.date, dt.date],
    window_min: int,
    target: str,
) -> None:
    """Create ``target`` (ScheduleSlot rows, data-model.md), ``{target}_days`` (one row per
    flight-day: slot_id, service_date, marketing_airline, flight_number, origin, dest,
    dep_local_min) and ``{target}_changes`` (slot_id, change_date, from_local_min,
    to_local_min) for joined schedule changes."""
    start, end = period
    days_in_period = (end - start).days + 1
    with tempfile.TemporaryDirectory(prefix="slots-") as tmp:
        slot_path = Path(tmp) / "slots.csv"
        day_path = Path(tmp) / "days.csv"
        change_path = Path(tmp) / "changes.csv"
        with (
            slot_path.open("w", newline="", encoding="utf-8") as fs,
            day_path.open("w", newline="", encoding="utf-8") as fd,
            change_path.open("w", newline="", encoding="utf-8") as fc,
        ):
            ws, wd, wc = (csv.writer(f, lineterminator="\n") for f in (fs, fd, fc))
            ws.writerow(
                [
                    "slot_id",
                    "marketing_airline",
                    "origin",
                    "dest",
                    "ref",
                    "lo",
                    "hi",
                    "days",
                    "numbers",
                ]
            )
            wd.writerow(
                [
                    "slot_id",
                    "service_date",
                    "marketing_airline",
                    "flight_number",
                    "origin",
                    "dest",
                    "dep_local_min",
                ]
            )
            wc.writerow(["slot_id", "change_date", "from_local_min", "to_local_min"])
            for (airline, origin, dest), records in _groups(con, flights, period):
                used: Counter[str] = Counter()
                for slot in assign_slots(records, window_min):
                    base = f"{airline}-{origin}-{dest}-{_hhmm(slot.ref_dep_local_min)}"
                    used[base] += 1
                    slot_id = base if used[base] == 1 else f"{base}-{used[base]}"
                    dates = {r.date for r in slot.records}
                    counts = Counter(r.flight_number for r in slot.records)
                    numbers = ";".join(
                        f"{n}={c}"
                        for n, c in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
                    )
                    times = [r.dep_local_min for r in slot.records]
                    ws.writerow(
                        [
                            slot_id,
                            airline,
                            origin,
                            dest,
                            slot.ref_dep_local_min,
                            min(times),
                            max(times),
                            len(dates),
                            numbers,
                        ]
                    )
                    for r in slot.records:
                        wd.writerow(
                            [
                                slot_id,
                                r.date.isoformat(),
                                airline,
                                r.flight_number[len(airline) :],
                                origin,
                                dest,
                                r.dep_local_min,
                            ]
                        )
                    for d, a, b in slot.changes:
                        wc.writerow([slot_id, d.isoformat(), a, b])

        def read(path: Path, types: str) -> str:
            p = str(path).replace("'", "''")
            return f"read_csv('{p}', header = true, columns = {{{types}}})"

        con.execute(
            f"""
            CREATE OR REPLACE TABLE {target} AS
            WITH s AS (
                SELECT * FROM {read(slot_path, _SLOT_COLUMNS)}
            )
            SELECT slot_id, marketing_airline, origin, dest,
                   ref AS ref_dep_local_min, lo AS min_dep_local_min, hi AS max_dep_local_min,
                   days AS scheduled_days,
                   round(days / {days_in_period}, 6) AS recurrence,
                   list_transform(string_split(numbers, ';'), lambda x: struct_pack(
                       flight_number := split_part(x, '=', 1),
                       share_of_days := round(CAST(split_part(x, '=', 2) AS INTEGER) / days, 6)
                   )) AS flight_numbers
            FROM s
            ORDER BY slot_id
            """
        )
        con.execute(
            f"""
            CREATE OR REPLACE TABLE {target}_days AS
            SELECT slot_id, service_date, marketing_airline, flight_number, origin, dest,
                   dep_local_min
            FROM {read(day_path, _DAY_COLUMNS)}
            ORDER BY slot_id, service_date
            """
        )
        con.execute(
            f"""
            CREATE OR REPLACE TABLE {target}_changes AS
            SELECT * FROM {read(change_path, _CHANGE_COLUMNS)}
            ORDER BY slot_id, change_date
            """
        )
