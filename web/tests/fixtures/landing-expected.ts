// What the landing page must show, worked out by hand from the committed data, never with
// the formatting code under test (FR-018). `RAW` repeats the data values these texts come
// from; a test fails when the data changes, so the texts are rechecked deliberately.
import type { RouteFile } from "@contract";

export const RAW = {
  a: {
    id: "LIT-ATL-LGA:DL1238+DL1700",
    count_feasible: 275,
    paired_days: 298,
    dep_local_min: 758,
    arr_local_min: 1153,
    layover_min: 99,
    travel_min: 327,
    not_connecting: 11,
    legs: ["DL3080", "DL524"],
  },
  b: {
    id: "LIT-ORD-LGA:UA1515+UA1800",
    count_feasible: 186,
    paired_days: 291,
    dep_local_min: 915,
    arr_local_min: 1275,
    layover_min: 50,
    travel_min: 299,
    not_connecting: 0,
    legs: ["UA4182", "UA1006"],
  },
  difference: 0.283644,
  ci_low: 0.223085,
  ci_high: 0.345678,
  shared_days: 242,
  start: "2024-07-01",
  end: "2025-06-30",
  run_at: "2026-11-28T01:51:17+00:00",
} as const;

/** 275/298 = 92.28%; 186/291 = 63.92%; 0.2836 = 28 points; 0.2231 and 0.3457 = 22 and 35. */
export const EXPECTED = {
  heading: "Little Rock (LIT) to New York (LGA)",
  comparison: "The example: Delta via ATL against United via ORD",
  summary: "Delta via ATL worked more often than United via ORD.",
  a: [
    "Worked more often",
    "Delta via ATL",
    "worked on 92% of 298 days, Jul 2024 – Jun 2025",
    "Most often DL3080, then DL524; flown under other numbers on some days",
    "12:38 pm local time",
    "7:13 pm local time",
    "1 h 39 min at ATL",
    "5 h 27 min",
    "11 days the two flights were not scheduled to connect",
  ],
  b: [
    "United via ORD",
    "worked on 64% of 291 days, Jul 2024 – Jun 2025",
    "Most often UA4182, then UA1006; flown under other numbers on some days",
    "3:15 pm local time",
    "9:15 pm local time",
    "50 min at ORD",
    "4 h 59 min",
  ],
  difference: ["+28 points", "95% interval +22 to +35 points, over 242 days both flew."],
  footer: ["Data period Jul 2024 – Jun 2025.", "Data built 28 Nov 2026."],
} as const;

/** Throws when the committed data no longer matches `RAW`, naming the first difference. */
export function checkRaw(landing: RouteFile, runAt: unknown): void {
  const actual = (id: string) => {
    const i = landing.itineraries.find((x) => x.itinerary_id === id);
    if (!i) throw new Error(`landing.json no longer has ${id}`);
    return {
      id,
      count_feasible: i.result.count_feasible,
      paired_days: i.result.paired_days,
      dep_local_min: i.schedule.dep_local_min,
      arr_local_min: i.schedule.arr_local_min,
      layover_min: i.schedule.layover_min,
      travel_min: i.schedule.travel_min,
      not_connecting: i.excluded_days.not_connecting,
      legs: i.find.legs.map((l) => l.flight_number),
    };
  };
  const comparison = landing.comparisons.find(
    (c) => c.itinerary_a === RAW.a.id && c.itinerary_b === RAW.b.id,
  );
  const now = {
    a: actual(RAW.a.id),
    b: actual(RAW.b.id),
    difference: comparison?.difference,
    ci_low: comparison?.ci_low,
    ci_high: comparison?.ci_high,
    shared_days: comparison?.shared_days,
    start: landing.period.start,
    end: landing.period.end,
    run_at: runAt,
  };
  if (JSON.stringify(now) !== JSON.stringify(RAW)) {
    throw new Error(
      "The landing data changed: recheck EXPECTED by hand and update RAW in " +
        `tests/fixtures/landing-expected.ts.\nnow: ${JSON.stringify(now)}`,
    );
  }
}
