import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { RouteFile } from "@contract";
import { memorySource } from "../../src/data";
import { clone, committedFiles, committedIndex, committedLanding } from "../fixtures/committed";
import { renderApp } from "../fixtures/render";

const index = committedIndex();

/** The committed files with the landing file changed by `edit`. */
function withLanding(edit: (landing: RouteFile) => void) {
  const files = committedFiles();
  const landing = clone(committedLanding());
  edit(landing);
  files["landing.json"] = landing;
  return memorySource(files);
}

function landingParts(landing: RouteFile) {
  const comparison = landing.comparisons.find(
    (c) => c.comparison_id === index.landing.comparison_id,
  );
  const a = landing.itineraries.find((i) => i.itinerary_id === comparison?.itinerary_a);
  const b = landing.itineraries.find((i) => i.itinerary_id === comparison?.itinerary_b);
  if (!comparison || !a || !b) throw new Error("fixture incomplete");
  return { comparison, a, b };
}

describe("display rules on edge-case data (spec, Edge Cases)", () => {
  it("shows 'insufficient data' and no percentage below the minimum sample (FR-003)", async () => {
    renderApp(
      withLanding((landing) => {
        const { b } = landingParts(landing);
        b.result = {
          status: "insufficient_data",
          rate: null,
          paired_days: 12,
          count_feasible: 9,
          definition: "connection_feasibility",
        };
      }),
    );
    await screen.findByRole("heading", { level: 2 });
    const [, second] = screen.getAllByRole("article");
    expect(second).toHaveTextContent("insufficient data (12 days)");
    expect(second?.textContent).not.toMatch(/worked on \d+%/);
    expect(second?.querySelector(".rate-value")).toBeNull();
  });

  it("says 'similar' when the interval includes zero (FR-002)", async () => {
    renderApp(
      withLanding((landing) => {
        const { comparison } = landingParts(landing);
        comparison.difference = 0.02;
        comparison.ci_low = -0.01;
        comparison.ci_high = 0.05;
      }),
    );
    await screen.findByRole("heading", { level: 2 });
    expect(document.body).toHaveTextContent(/worked on a similar share of days/i);
    expect(document.body.textContent).not.toMatch(/worked more often/i);
  });

  it("marks an arrival after midnight with +1 day", async () => {
    renderApp(
      withLanding((landing) => {
        const { a } = landingParts(landing);
        a.schedule.dep_local_min = 1320; // 10:00 pm
        a.schedule.travel_min = 330;
        a.schedule.arr_local_min = 390; // 6:30 am, three time zones east
      }),
    );
    await screen.findByRole("heading", { level: 2 });
    const [first] = screen.getAllByRole("article");
    expect(first).toHaveTextContent("6:30 am");
    expect(first).toHaveTextContent("+1 day");
  });

  it("names both airlines when the two flights are on different airlines", async () => {
    renderApp(
      withLanding((landing) => {
        const { a } = landingParts(landing);
        a.airline_out = "AS";
      }),
    );
    await screen.findByRole("heading", { level: 2 });
    const [first] = screen.getAllByRole("article");
    expect(first).toHaveTextContent("Delta and Alaska via ATL");
  });
});
