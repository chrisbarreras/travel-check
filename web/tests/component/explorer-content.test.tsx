// What each explorer view says about each itinerary (specs/004 US1-2, US1-4, Edge Cases).
import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { RouteFile } from "@contract";
import { memorySource } from "../../src/data";
import { flightsText, timesText } from "../../src/explorer/ItineraryList";
import { barTimes } from "../../src/explorer/Timeline";
import { duration } from "../../src/format";
import { byDeparture } from "../../src/format/timeline";
import { clone, committedFiles, committedIndex } from "../fixtures/committed";
import { renderApp } from "../fixtures/render";

const files = committedFiles();
const index = committedIndex();
const route = (id: string) => files[`routes/${id}.json`] as RouteFile;
const list = () => screen.getByRole("region", { name: /Itineraries, by departure time/ });

function open(search: string, source = memorySource(files)) {
  window.history.replaceState(null, "", `/${search}`);
  renderApp(source);
}

afterEach(() => {
  window.history.replaceState(null, "", "/");
  vi.restoreAllMocks();
});

describe("list cards (FR-005)", () => {
  it.each(index.routes.map((r) => r.route_id))(
    "%s: each card names its flights, times and layover",
    async (routeId) => {
      open(`?route=${routeId}`);
      await screen.findByRole("region", { name: /Itineraries/ });
      for (const it of route(routeId).itineraries) {
        const card = list().querySelector(`[data-itinerary="${CSS.escape(it.itinerary_id)}"]`);
        expect(card, it.itinerary_id).not.toBeNull();
        const text = card?.textContent ?? "";
        for (const leg of it.find.legs) expect(text).toContain(leg.flight_number);
        expect(text).toContain(flightsText(it));
        expect(text).toContain(timesText(it));
        expect(text).toContain(`Layover ${duration(it.schedule.layover_min)} at ${it.hub}`);
      }
    },
  );
});

describe("an insufficient-data itinerary (spec, Edge Cases; Principle I)", () => {
  it("is listed in departure order with 'insufficient data' and no percentage", async () => {
    const changed = clone(route("MCO-LAS"));
    const ordered = byDeparture(changed.itineraries);
    const target = ordered[3];
    if (!target) throw new Error("fixture");
    target.result = {
      status: "insufficient_data",
      rate: null,
      paired_days: 12,
      count_feasible: 9,
      definition: "connection_feasibility",
    };
    // A comparison with an insufficient itinerary is not published, so drop its comparisons.
    changed.comparisons = changed.comparisons.filter(
      (c) => c.itinerary_a !== target.itinerary_id && c.itinerary_b !== target.itinerary_id,
    );
    open("?route=MCO-LAS", memorySource({ ...files, "routes/MCO-LAS.json": changed }));
    await screen.findByRole("region", { name: /Itineraries/ });
    const buttons = within(list()).getAllByRole("button");
    expect(buttons.map((b) => b.getAttribute("data-itinerary"))).toEqual(
      ordered.map((i) => i.itinerary_id),
    );
    const card = buttons[3];
    expect(card).toHaveTextContent("insufficient data (12 days");
    expect(card?.textContent).not.toMatch(/\d+%/);
    // The timeline shows schedules only, never rates, for any itinerary.
    const timeline = screen.getByRole("region", { name: "Timeline" });
    expect(timeline.textContent).not.toMatch(/\d+%/);
  });
});

describe("route history (US2-2)", () => {
  it("adds an entry for a deliberate route choice, sharing one only for rapid changes", async () => {
    const user = userEvent.setup();
    const push = vi.spyOn(window.history, "pushState");
    let now = 1_000_000;
    vi.spyOn(Date, "now").mockImplementation(() => now);
    open("");
    await screen.findByRole("region", { name: /Itineraries/ });
    const picker = screen.getByLabelText("Route");
    await user.selectOptions(picker, "MCO-LAS");
    now += 200; // a keypress later
    await user.selectOptions(picker, "HNL-BOS");
    expect(push).toHaveBeenCalledTimes(1);
    now += 5_000; // a deliberate choice later
    await user.selectOptions(picker, "SJC-ATL");
    expect(push).toHaveBeenCalledTimes(2);
    await waitFor(() => {
      expect(window.location.search).toBe("?route=SJC-ATL");
    });
  });
});

describe("timeline labels (US1-4)", () => {
  it("marks hub times and the arrival that fall on a later local day", () => {
    const overnight = route("HNL-BOS").itineraries.find(
      (i) => i.itinerary_id === "HNL-ATL-BOS:DL1522+DL0705",
    );
    if (!overnight) throw new Error("fixture");
    const text = barTimes(overnight, "HNL", "BOS");
    expect(text).toMatch(/^3:22 pm HNL → \d+:\d\d [ap]m \+1 day–\d+:\d\d [ap]m \+1 day ATL → /);
    expect(text).toMatch(/\+1 day BOS$/);
  });

  it("has no day marker on a same-day itinerary", () => {
    const sameDay = route("LIT-LGA").itineraries.find(
      (i) => i.itinerary_id === "LIT-ATL-LGA:DL1238+DL1700",
    );
    if (!sameDay) throw new Error("fixture");
    expect(barTimes(sameDay, "LIT", "LGA")).toBe(
      "12:38 pm LIT → 3:13 pm–4:52 pm ATL → 7:13 pm LGA",
    );
  });
});
