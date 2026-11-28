import { describe, expect, it } from "vitest";
import type { RouteFile } from "@contract";
import { buildRouteView, ROUTE_DEFINITIONS } from "../../src/data/route";
import { clone, committedFiles, committedIndex } from "../fixtures/committed";

const index = committedIndex();
const files = committedFiles();
const routeFile = (id: string) => clone(files[`routes/${id}.json`] as RouteFile);

describe("buildRouteView (FR-011)", () => {
  it.each(index.routes.map((r) => r.route_id))("accepts the committed route %s", (id) => {
    const view = buildRouteView(index, routeFile(id), id);
    expect(view.ok).toBe(true);
    if (!view.ok) return;
    expect(view.value.itineraries.map((i) => i.itinerary_id).sort()).toEqual(
      routeFile(id).itineraries.map((i) => i.itinerary_id).sort(),
    );
    expect(view.value.origin.code).toBe(id.slice(0, 3));
    expect(view.value.dest.code).toBe(id.slice(4));
  });

  it("orders itineraries by departure", () => {
    const view = buildRouteView(index, routeFile("LIT-LGA"), "LIT-LGA");
    if (!view.ok) throw new Error("expected ok");
    const deps = view.value.itineraries.map((i) => i.schedule.dep_local_min);
    expect(deps).toEqual([...deps].sort((x, y) => x - y));
  });

  it("rejects a file for another route", () => {
    expect(buildRouteView(index, routeFile("LIT-LGA"), "MCO-LAS")).toMatchObject({
      ok: false,
      error: { kind: "invalid" },
    });
  });

  it("rejects a rate that disagrees with its counts", () => {
    const route = routeFile("LIT-LGA");
    const first = route.itineraries[0];
    if (!first) throw new Error("no itinerary");
    first.result.rate = 0.1;
    expect(buildRouteView(index, route, "LIT-LGA").ok).toBe(false);
  });

  it("rejects an unordered comparison", () => {
    const route = routeFile("LIT-LGA");
    const c = route.comparisons[0];
    if (!c) throw new Error("no comparison");
    c.difference = -0.1;
    expect(buildRouteView(index, route, "LIT-LGA").ok).toBe(false);
  });

  it("rejects a hub missing from the index's airports", () => {
    const partial = { ...index, airports: index.airports.filter((a) => a.code !== "ATL") };
    expect(buildRouteView(partial, routeFile("LIT-LGA"), "LIT-LGA")).toMatchObject({
      ok: false,
      error: { kind: "invalid", file: "index.json" },
    });
  });

  it.each(ROUTE_DEFINITIONS)("rejects an index without the %s definition", (key) => {
    const partial = { ...index, definitions: index.definitions.filter((d) => d.key !== key) };
    expect(buildRouteView(partial, routeFile("LIT-LGA"), "LIT-LGA").ok).toBe(false);
  });
});
