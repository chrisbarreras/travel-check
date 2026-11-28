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
    const atHub = coords.some(([lon, lat]) => Math.abs((lon ?? 0) + 84.43) < 0.01 && Math.abs((lat ?? 0) - 33.64) < 0.01);
    expect(atHub).toBe(true);
  });

  it("is curved, not two straight segments", () => {
    const coords = paths.features[0]?.geometry.coordinates ?? [];
    expect(coords.length).toBeGreaterThan(10);
  });

  it("rejects an airport missing from the list", () => {
    expect(() => routePaths(airports, "LIT", "BOS", itineraries)).toThrow(/BOS/);
  });
});

describe("airportPoints and bounds", () => {
  it("marks the hubs and the route ends", () => {
    expect(airportPoints(airports, "LIT", "LGA", itineraries).map((p) => [p.code, p.role])).toEqual([
      ["LIT", "origin"],
      ["LGA", "destination"],
      ["ATL", "hub"],
      ["ORD", "hub"],
    ]);
  });

  it("covers every point with a margin", () => {
    const b = bounds(airportPoints(airports, "LIT", "LGA", itineraries));
    expect(b[0][0]).toBeLessThan(-92.22);
    expect(b[1][0]).toBeGreaterThan(-73.87);
    expect(b[0][1]).toBeLessThan(33.64);
    expect(b[1][1]).toBeGreaterThan(41.98);
  });
});
