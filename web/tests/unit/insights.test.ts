import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import type { RouteFile } from "@contract";
import { findUrl } from "../../src/insights/find";
import { meterDots } from "../../src/insights/meter";
import { monthBars } from "../../src/insights/months";
import { slackRate } from "../../src/insights/slackRate";
import { parseTransfer, withTransfer } from "../../src/selection/transfer";
import { committedFiles, committedIndex } from "../fixtures/committed";

interface SharedCase {
  name: string;
  slack_min: (number | null)[];
  outcome: string;
  transfer_min: number;
  boarding_cutoff_min: number;
  min_sample_days: number;
  expected: { paired_days: number; count_feasible: number; status: string; rate: number | null };
}

const shared = JSON.parse(
  readFileSync(join(process.cwd(), "..", "shared", "test-cases", "slack-feasibility.json"), "utf8"),
) as { cases: SharedCase[] };

describe("slackRate: the shared test cases (constitution II; SC-002)", () => {
  it.each(shared.cases.map((c) => [c.name, c] as const))("%s", (_name, c) => {
    const result = slackRate(
      { day_offset: c.slack_min.map((_, i) => i), outcome: c.outcome, slack_min: c.slack_min },
      c.transfer_min,
      c.boarding_cutoff_min,
      c.min_sample_days,
    );
    expect(result).toEqual(c.expected);
  });
});

describe("slackRate reproduces every published rate at its default (SC-001)", () => {
  const index = committedIndex();
  const routes = Object.entries(committedFiles())
    .filter(([path]) => path.startsWith("routes/"))
    .map(([, file]) => file as RouteFile);
  const itineraries = routes.flatMap((r) => r.itineraries);

  it("covers all 144 itineraries", () => {
    expect(itineraries).toHaveLength(144);
  });

  it.each(itineraries.map((i) => [i.itinerary_id, i] as const))("%s", (_id, it) => {
    const result = slackRate(
      it.daily,
      it.min_connection_min,
      index.assumptions.boarding_cutoff_min,
      index.assumptions.min_sample_days,
    );
    expect(result).toEqual({
      paired_days: it.result.paired_days,
      count_feasible: it.result.count_feasible,
      status: it.result.status,
      rate: it.result.rate,
    });
  });
});

describe("meterDots (docs/design.md, Reliability meter)", () => {
  it.each([
    [0.922819, 9],
    [0.95, 10], // halves away from zero
    [0.949999, 9],
    [0.05, 1],
    [0.04, 0],
    [1, 10],
    [0, 0],
  ])("%f fills %i of 10", (rate, filled) => {
    expect(meterDots(rate)).toBe(filled);
  });
});

describe("monthBars", () => {
  const notes = [
    {
      note_id: "crowdstrike-2024-07",
      start: "2024-07-19",
      end: "2024-07-24",
      text: "A global IT outage",
      source_url: "https://example.org",
      airlines: ["DL"],
      airports: [],
    },
  ];
  it("labels months, keeps counts below the minimum, dashes months with no flights", () => {
    const bars = monthBars(
      [
        {
          month: "2024-07",
          status: "ok",
          rate: 0.935484,
          paired_days: 31,
          note_ids: ["crowdstrike-2024-07"],
        },
        {
          month: "2024-08",
          status: "insufficient_data",
          rate: null,
          paired_days: 12,
          note_ids: [],
        },
        { month: "2024-09", status: "no_flights", rate: null, paired_days: 0, note_ids: [] },
      ],
      notes,
    );
    expect(bars).toEqual([
      {
        month: "2024-07",
        label: "Jul 2024",
        kind: "ok",
        percent: 94,
        days: 31,
        notes: ["crowdstrike-2024-07"],
      },
      {
        month: "2024-08",
        label: "Aug 2024",
        kind: "insufficient",
        percent: null,
        days: 12,
        notes: [],
      },
      { month: "2024-09", label: "Sep 2024", kind: "none", percent: null, days: 0, notes: [] },
    ]);
  });
});

describe("findUrl (FR-009)", () => {
  it("prefills a Google Flights text search with the route and airlines", () => {
    expect(findUrl({ origin: "LIT", dest: "LGA", airlines: ["DL"], legs: [] }, ["Delta"])).toBe(
      "https://www.google.com/travel/flights?q=" +
        encodeURIComponent("Flights from LIT to LGA on Delta"),
    );
    expect(
      findUrl({ origin: "HNL", dest: "BOS", airlines: ["DL", "AS"], legs: [] }, [
        "Delta",
        "Alaska",
      ]),
    ).toContain(encodeURIComponent("on Delta and Alaska"));
  });
});

describe("the transfer parameter (FR-003)", () => {
  it("reads a valid setting and ignores others", () => {
    expect(parseTransfer("?route=A-B&transfer=60")).toBe(60);
    expect(parseTransfer("?transfer=62")).toBeNull(); // not a 5-minute step
    expect(parseTransfer("?transfer=10")).toBeNull(); // below 15
    expect(parseTransfer("?transfer=125")).toBeNull(); // above 120
    expect(parseTransfer("?transfer=abc")).toBeNull();
    expect(parseTransfer("?route=A-B")).toBeNull();
  });

  it("writes the setting, and leaves it out at the default", () => {
    expect(withTransfer("?route=A-B&itinerary=x", 60, 30)).toBe(
      "?route=A-B&itinerary=x&transfer=60",
    );
    expect(withTransfer("?route=A-B&itinerary=x&transfer=60", 30, 30)).toBe(
      "?route=A-B&itinerary=x",
    );
  });
});
