import { describe, expect, it } from "vitest";
import { parseSelection, resolveItinerary, serializeSelection } from "../../src/selection/url";

const index = {
  routes: [{ route_id: "LIT-LGA" }, { route_id: "MCO-LAS" }],
  landing: { route_id: "LIT-LGA" },
};

describe("parseSelection (ADR-0010)", () => {
  it("opens the landing route when the address has no parameters", () => {
    expect(parseSelection("", index)).toEqual({
      selection: { routeId: "LIT-LGA", itineraryId: null },
      note: null,
    });
  });

  it("reads a route and an itinerary", () => {
    expect(parseSelection("?route=MCO-LAS&itinerary=MCO-ATL-LAS%3ADL1%2BDL2", index)).toEqual({
      selection: { routeId: "MCO-LAS", itineraryId: "MCO-ATL-LAS:DL1+DL2" },
      note: null,
    });
  });

  it("falls back to the default view with a note for an unknown route", () => {
    expect(parseSelection("?route=XXX-YYY&itinerary=a", index)).toEqual({
      selection: { routeId: "LIT-LGA", itineraryId: null },
      note: "The linked example was not found, so the default example is shown.",
    });
  });

  it("ignores unknown parameters", () => {
    expect(parseSelection("?route=MCO-LAS&utm_source=cv", index).note).toBeNull();
  });
});

describe("resolveItinerary (after the route file loads)", () => {
  const ids = ["a", "b"];
  it("keeps an itinerary on the route", () => {
    expect(resolveItinerary({ routeId: "MCO-LAS", itineraryId: "b" }, ids, "LIT-LGA")).toEqual({
      selection: { routeId: "MCO-LAS", itineraryId: "b" },
      note: null,
    });
  });

  it("opens the default view, with a note, for an itinerary not on the route (FR-010)", () => {
    expect(resolveItinerary({ routeId: "MCO-LAS", itineraryId: "z" }, ids, "LIT-LGA")).toEqual({
      selection: { routeId: "LIT-LGA", itineraryId: null },
      note: "The linked example was not found, so the default example is shown.",
    });
  });
});

describe("serializeSelection", () => {
  it("gives the default view an empty query", () => {
    expect(serializeSelection({ routeId: "LIT-LGA", itineraryId: null }, "LIT-LGA")).toBe("");
  });

  it("round-trips through parseSelection", () => {
    const selection = { routeId: "MCO-LAS", itineraryId: "MCO-ATL-LAS:DL1+DL2" };
    const search = serializeSelection(selection, "LIT-LGA");
    expect(search).toBe("?route=MCO-LAS&itinerary=MCO-ATL-LAS%3ADL1%2BDL2");
    expect(parseSelection(search, index).selection).toEqual(selection);
  });

  it("keeps the route when it is the landing route with an itinerary", () => {
    expect(serializeSelection({ routeId: "LIT-LGA", itineraryId: "x" }, "LIT-LGA")).toBe(
      "?route=LIT-LGA&itinerary=x",
    );
  });
});
