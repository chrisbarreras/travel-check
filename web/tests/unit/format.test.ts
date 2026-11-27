import { describe, expect, it } from "vitest";
import {
  arrivalDayOffset,
  builtDate,
  duration,
  excludedText,
  flightNumbers,
  intervalText,
  localTime,
  percentOf,
  periodText,
  points,
  rateText,
  signed,
  similarOrMore,
} from "../../src/format";

describe("percentOf (whole percent, halves away from zero)", () => {
  it.each([
    [275, 298, 92],
    [186, 291, 64],
    [1, 200, 1], // 0.5 % rounds up
    [199, 200, 100], // 99.5 % rounds up
    [1, 2, 50],
    [0, 30, 0],
    [30, 30, 100],
    [1, 128, 1], // 0.78125 %
    [77, 128, 60], // 60.15625 %
    [1, 3, 33],
    [2, 3, 67],
  ])("%i of %i days is %i%%", (feasible, paired, expected) => {
    expect(percentOf(feasible, paired)).toBe(expected);
  });

  it("is exact where floating point would drift", () => {
    // 0.145 * 100 is 14.499999999999998 in floating point.
    expect(percentOf(29, 200)).toBe(15);
    expect(percentOf(57, 200)).toBe(29); // 28.5 %
  });

  it("rejects an empty sample", () => {
    expect(() => percentOf(0, 0)).toThrow();
  });
});

describe("points (signed whole points from a stored share)", () => {
  it.each([
    [0.283644, 28],
    [0.223085, 22],
    [0.345678, 35],
    [0.005, 1],
    [-0.005, -1], // halves away from zero, symmetric
    [-0.015, -2],
    [0.004999, 0],
    [-0.004999, 0],
    [0, 0],
  ])("%f is %i points", (share, expected) => {
    expect(points(share)).toBe(expected);
  });

  it("never returns negative zero", () => {
    expect(Object.is(points(-0.001), -0)).toBe(false);
  });
});

describe("signed", () => {
  it("marks positive, negative and zero", () => {
    expect(signed(28)).toBe("+28");
    expect(signed(-3)).toBe("−3");
    expect(signed(0)).toBe("0");
  });
});

describe("intervalText", () => {
  it("states the interval in whole points", () => {
    expect(intervalText(0.223085, 0.345678)).toBe("95% interval +22 to +35 points");
    expect(intervalText(-0.012, 0.05)).toBe("95% interval −1 to +5 points");
  });
});

describe("similarOrMore (on exact values, never rounded ones)", () => {
  it("is 'more' only when the whole interval is above zero", () => {
    expect(similarOrMore(0.223085, 0.345678)).toBe("more");
    expect(similarOrMore(0, 0.1)).toBe("similar");
    expect(similarOrMore(-0.02, 0.1)).toBe("similar");
  });

  it("does not call a tiny positive lower bound 'similar' because it rounds to 0", () => {
    expect(points(0.001)).toBe(0);
    expect(similarOrMore(0.001, 0.2)).toBe("more");
  });
});

describe("localTime", () => {
  it.each([
    [758, "12:38 pm", 0],
    [1153, "7:13 pm", 0],
    [0, "12:00 am", 0],
    [720, "12:00 pm", 0],
    [59, "12:59 am", 0],
    [1439, "11:59 pm", 0],
    [1440, "12:00 am", 1],
    [1500, "1:00 am", 1],
    [2880 + 65, "1:05 am", 2],
  ])("%i minutes is %s (+%i day)", (minutes, text, dayOffset) => {
    expect(localTime(minutes)).toEqual({ text, dayOffset });
  });

  it("rejects negative minutes", () => {
    expect(() => localTime(-1)).toThrow();
  });
});

describe("arrivalDayOffset (from clock times and travel time only)", () => {
  it.each([
    // LIT 12:38 pm CT → LGA 7:13 pm ET, 5 h 27 min: same day.
    [758, 1153, 327, 0],
    // LAX 10:00 pm PT → BOS 6:30 am ET, 5 h 30 min: next day.
    [1320, 390, 330, 1],
    // BOS 11:00 pm ET → LAX 1:30 am PT, 5 h 30 min: next day.
    [1380, 90, 330, 1],
    // HNL 11:00 pm HST → BOS 3:40 pm ET, 10 h 40 min: next day.
    [1380, 940, 640, 1],
    // JFK 6:00 am ET → LAX 9:10 am PT, 6 h 10 min: same day.
    [360, 550, 370, 0],
    // ORD 11:50 pm CT → ORD 12:20 am CT, 30 min: next day.
    [1430, 20, 30, 1],
  ])("dep %i, arr %i, travel %i → %i", (dep, arr, travel, expected) => {
    expect(arrivalDayOffset({ dep_local_min: dep, arr_local_min: arr, travel_min: travel })).toBe(
      expected,
    );
  });
});

describe("duration", () => {
  it.each([
    [99, "1 h 39 min"],
    [45, "45 min"],
    [60, "1 h"],
    [327, "5 h 27 min"],
    [0, "0 min"],
  ])("%i minutes is %s", (minutes, text) => {
    expect(duration(minutes)).toBe(text);
  });
});

describe("periodText and builtDate", () => {
  it("names the months without time-zone arithmetic", () => {
    expect(periodText({ start: "2024-07-01", end: "2025-06-30", db1b_quarters: [] })).toBe(
      "Jul 2024 – Jun 2025",
    );
  });

  it("gives the UTC calendar date of the build", () => {
    expect(builtDate("2026-11-26T21:10:45+00:00")).toBe("26 Nov 2026");
    expect(builtDate("2026-01-05T00:00:00Z")).toBe("5 Jan 2026");
  });

  it("rejects malformed dates", () => {
    expect(() =>
      periodText({ start: "2024-13-01", end: "2025-06-30", db1b_quarters: [] }),
    ).toThrow();
    expect(() => builtDate("yesterday")).toThrow();
    expect(() => builtDate("2026-13-45T00:00:00Z")).toThrow();
    expect(() => builtDate("2026-02-31T00:00:00Z")).toThrow();
  });
});

describe("rateText", () => {
  it("gives a whole percent with its days when the sample is sufficient", () => {
    expect(
      rateText({
        status: "ok",
        rate: 0.922819,
        paired_days: 298,
        count_feasible: 275,
        definition: "connection_feasibility",
      }),
    ).toEqual({ kind: "ok", percent: 92, days: 298, text: "worked on 92% of 298 days" });
  });

  it("carries the data period when given", () => {
    const rate = {
      status: "ok",
      rate: 0.922819,
      paired_days: 298,
      count_feasible: 275,
      definition: "connection_feasibility",
    } as const;
    expect(rateText(rate, "Jul 2024 – Jun 2025").text).toBe(
      "worked on 92% of 298 days, Jul 2024 – Jun 2025",
    );
  });

  it("never gives a percentage below the minimum sample", () => {
    const result = rateText({
      status: "insufficient_data",
      rate: null,
      paired_days: 12,
      count_feasible: 9,
      definition: "connection_feasibility",
    });
    expect(result).toEqual({ kind: "insufficient", days: 12, text: "insufficient data (12 days)" });
    expect(result.text).not.toMatch(/%/);
  });
});

describe("excludedText", () => {
  it("lists only non-zero reasons", () => {
    expect(excludedText({ not_connecting: 11, end_of_period: 0, quality: 0 })).toEqual([
      "11 days the two flights were not scheduled to connect",
    ]);
    expect(excludedText({ not_connecting: 0, end_of_period: 0, quality: 0 })).toEqual([]);
    expect(excludedText({ not_connecting: 1, end_of_period: 2, quality: 3 })).toEqual([
      "1 day the two flights were not scheduled to connect",
      "2 days at the end of the data period",
      "3 days that failed the data-quality checks",
    ]);
  });
});

describe("flightNumbers", () => {
  it("names each leg's most frequent number and never shows its share", () => {
    const result = flightNumbers([
      { flight_number: "DL3080", share_of_days: 0.352751 },
      { flight_number: "DL524", share_of_days: 0.608309 },
    ]);
    expect(result).toEqual({ numbers: ["DL3080", "DL524"], varies: true });
    expect(JSON.stringify(result)).not.toMatch(/%/);
  });

  it("notes other numbers only when a leg used them on more than 5% of days", () => {
    expect(
      flightNumbers([
        { flight_number: "UA4182", share_of_days: 0.96 },
        { flight_number: "UA1006", share_of_days: 0.95 },
      ]),
    ).toEqual({ numbers: ["UA4182", "UA1006"], varies: false });
    expect(flightNumbers([{ flight_number: "UA1", share_of_days: 0.9496 }]).varies).toBe(true);
  });
});
