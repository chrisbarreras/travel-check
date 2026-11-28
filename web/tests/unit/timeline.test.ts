import { describe, expect, it } from "vitest";
import { byDeparture, timelineRows } from "../../src/format/timeline";

const it_ = (id: string, dep: number, inbound: number, layover: number, travel: number) => ({
  itinerary_id: id,
  schedule: { dep_local_min: dep, inbound_min: inbound, layover_min: layover, travel_min: travel },
});

describe("byDeparture (never by rate; spec Clarifications)", () => {
  it("orders by scheduled departure, then by id", () => {
    const ordered = byDeparture([it_("c", 900, 60, 60, 300), it_("b", 600, 60, 60, 300), it_("a", 900, 60, 60, 300)]);
    expect(ordered.map((i) => i.itinerary_id)).toEqual(["b", "a", "c"]);
  });

  it("does not change its input", () => {
    const input = [it_("b", 900, 60, 60, 300), it_("a", 600, 60, 60, 300)];
    byDeparture(input);
    expect(input.map((i) => i.itinerary_id)).toEqual(["b", "a"]);
  });
});

describe("timelineRows", () => {
  it("places each bar from the earliest departure, with segments summing to travel time", () => {
    const { rows, start, extent } = timelineRows([
      it_("late", 758, 95, 99, 327),
      it_("early", 600, 60, 45, 300),
    ]);
    expect(start).toBe(600);
    expect(rows).toEqual([
      { id: "early", offset: 0, inbound: 60, layover: 45, outbound: 195 },
      { id: "late", offset: 158, inbound: 95, layover: 99, outbound: 133 },
    ]);
    expect(extent).toBe(485); // 158 + 327
    for (const r of rows) expect(r.inbound + r.layover + r.outbound).toBeGreaterThan(0);
  });

  it("is empty for no itineraries", () => {
    expect(timelineRows([])).toEqual({ rows: [], start: 0, extent: 0 });
  });

  it("never gives a negative segment", () => {
    const { rows } = timelineRows([it_("x", 0, 200, 150, 300)]);
    expect(rows[0]?.outbound).toBe(0);
  });
});
