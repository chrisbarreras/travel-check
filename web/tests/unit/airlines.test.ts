import { describe, expect, it } from "vitest";
import { airlineName } from "../../src/format/airlines";

import { committedFiles } from "../fixtures/committed";
import type { RouteFile } from "@contract";

function routeFiles(): RouteFile[] {
  return Object.entries(committedFiles())
    .filter(([path]) => path === "landing.json" || path.startsWith("routes/"))
    .map(([, file]) => file as RouteFile);
}

describe("airlineName", () => {
  it("names every airline in the committed showcase files", () => {
    const codes = new Set(
      routeFiles().flatMap((file) => file.itineraries.flatMap((i) => [i.airline, i.airline_out])),
    );
    expect(codes.size).toBeGreaterThan(0);
    for (const code of codes) {
      expect(airlineName(code), code).not.toBe(code);
    }
  });

  it("falls back to the code for an unknown airline", () => {
    expect(airlineName("ZZ")).toBe("ZZ");
  });
});
