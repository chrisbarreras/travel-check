import { describe, expect, it } from "vitest";
import { airportPoints, bounds, routePaths } from "../../src/map/geometry";

const airports = [
  { code: "ATL", name: "Atlanta", city: "Atlanta", lat: 33.64, lon: -84.43 },
  { code: "LGA", name: "LaGuardia", city: "New York", lat: 40.78, lon: -73.87 },
  { code: "LIT", name: "Little Rock", city: "Little Rock", lat: 34.73, lon: -92.22 },
  { code: "ORD", name: "O'Hare", city: "Chicago", lat: 41.98, lon: -87.9 },
];
const itineraries = [
  { itinerary_id: "a", hub: "ATL" },
  { itinerary_id: "b", hub: "ORD" },
];

describe("routePaths (pure map geometry, constitution II)", () => {
  const paths = routePaths(airports, "LIT", "LGA", itineraries);

  it("draws one line per itinerary, through its hub", () => {
    expect(paths.features.map((f) => f.properties)).toEqual([
      { itinerary_id: "a", hub: "ATL" },
      { itinerary_id: "b", hub: "ORD" },
    ]);
    const coords = paths.features[0]?.geometry.coordinates ?? [];
    expect(coords[0]?.[0]).toBeCloseTo(-92.22, 2);
    expect(coords.at(-1)?.[0]).toBeCloseTo(-73.87, 2);
    const atHub = coords.some(
      ([lon, lat]) => Math.abs(lon + 84.43) < 0.01 && Math.abs(lat - 33.64) < 0.01,
    );
    expect(atHub).toBe(true);
  });

  it("is curved: the arc's middle leaves the straight line between its ends", () => {
    // LIT to ATL is the first arc: 32 points (indexes 0 to 31).
    const coords = paths.features[0]?.geometry.coordinates ?? [];
    const [start, mid, end] = [coords[0], coords[16], coords[31]];
    if (!start || !mid || !end) throw new Error("arc too short");
    const chordLat = start[1] + ((mid[0] - start[0]) / (end[0] - start[0])) * (end[1] - start[1]);
    // A great circle bends toward the pole: north of the straight line on the map.
    expect(end).toEqual([expect.closeTo(-84.43, 2), expect.closeTo(33.64, 2)]);
    expect(mid[1] - chordLat).toBeGreaterThan(0.01);
  });

  it("rejects an airport missing from the list", () => {
    expect(() => routePaths(airports, "LIT", "BOS", itineraries)).toThrow(/BOS/);
  });
});

describe("airportPoints and bounds", () => {
  it("marks the hubs and the route ends", () => {
    expect(airportPoints(airports, "LIT", "LGA", itineraries).map((p) => [p.code, p.role])).toEqual(
      [
        ["LIT", "origin"],
        ["LGA", "destination"],
        ["ATL", "hub"],
        ["ORD", "hub"],
      ],
    );
  });

  it("covers every point with a margin", () => {
    const b = bounds(airportPoints(airports, "LIT", "LGA", itineraries));
    expect(b[0][0]).toBeLessThan(-92.22);
    expect(b[1][0]).toBeGreaterThan(-73.87);
    expect(b[0][1]).toBeLessThan(33.64);
    expect(b[1][1]).toBeGreaterThan(41.98);
  });
});
