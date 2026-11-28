// The explorer's linked views and the address (specs/004 US1, US2). The real map needs WebGL,
// so jsdom uses a stand-in with one button per path; e2e tests cover the real map.
import { act, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { RouteFile } from "@contract";
import { byDeparture } from "../../src/format/timeline";
import { committedFiles, committedIndex } from "../fixtures/committed";
import { renderApp } from "../fixtures/render";

vi.mock("../../src/map/MapView", () => ({
  default: ({
    itineraries,
    selectedId,
    onSelect,
  }: {
    itineraries: { itinerary_id: string }[];
    selectedId: string | null;
    onSelect: (id: string) => void;
  }) => (
    <div data-testid="map">
      {itineraries.map((i) => (
        <button
          key={i.itinerary_id}
          type="button"
          data-map-path={i.itinerary_id}
          data-selected={i.itinerary_id === selectedId}
          onClick={() => {
            onSelect(i.itinerary_id);
          }}
        >
          path {i.itinerary_id}
        </button>
      ))}
    </div>
  ),
}));

const index = committedIndex();
const files = committedFiles();
const route = (id: string) => files[`routes/${id}.json`] as RouteFile;

function open(search: string) {
  window.history.replaceState(null, "", `/${search}`);
  renderApp();
}

afterEach(() => {
  window.history.replaceState(null, "", "/");
});

const list = () => screen.getByRole("region", { name: /Itineraries, by departure time/ });
const timeline = () => screen.getByRole("region", { name: "Timeline" });

describe("the explorer (US1)", () => {
  it("opens on the landing route, with its itineraries in departure order", async () => {
    open("");
    await screen.findByRole("region", { name: /Itineraries/ });
    const ids = within(list())
      .getAllByRole("button")
      .map((b) => b.getAttribute("data-itinerary"));
    expect(ids).toEqual(
      byDeparture(route(index.landing.route_id).itineraries).map((i) => i.itinerary_id),
    );
    expect(await screen.findByRole("region", { name: /^The example:/ })).toBeInTheDocument();
  });

  it("selecting in the list selects in the timeline, the map and the detail panel", async () => {
    const user = userEvent.setup();
    open("");
    await screen.findByRole("region", { name: /Itineraries/ });
    const [, second] = within(list()).getAllByRole("button");
    if (!second) throw new Error("route has one itinerary");
    const id = second.getAttribute("data-itinerary") ?? "";
    await user.click(second);
    expect(second).toHaveAttribute("aria-pressed", "true");
    expect(second).toHaveTextContent("Selected");
    const row = timeline().querySelector(`[data-itinerary="${CSS.escape(id)}"]`);
    expect(row).toHaveAttribute("aria-pressed", "true");
    expect(await screen.findByTestId("map")).toBeInTheDocument();
    expect(document.querySelector(`[data-map-path="${CSS.escape(id)}"]`)).toHaveAttribute(
      "data-selected",
      "true",
    );
    expect(screen.queryByRole("region", { name: /^The example:/ })).not.toBeInTheDocument();
    expect(window.location.search).toBe(
      `?route=${index.landing.route_id}&itinerary=${encodeURIComponent(id)}`,
    );
  });

  it("selecting on the timeline or the map selects in the list", async () => {
    const user = userEvent.setup();
    open("");
    await screen.findByRole("region", { name: /Itineraries/ });
    const rows = within(timeline()).getAllByRole("button");
    const last = rows.at(-1);
    if (!last) throw new Error("no rows");
    await user.click(last);
    const id = last.getAttribute("data-itinerary") ?? "";
    expect(list().querySelector(`[data-itinerary="${CSS.escape(id)}"]`)).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    const path = (await screen.findByTestId("map")).querySelector("button");
    if (!path) throw new Error("no path");
    await user.click(path);
    const pathId = path.getAttribute("data-map-path") ?? "";
    expect(list().querySelector(`[data-itinerary="${CSS.escape(pathId)}"]`)).toHaveAttribute(
      "aria-pressed",
      "true",
    );
  });

  it("choosing a route shows that route only", async () => {
    const user = userEvent.setup();
    open("");
    await screen.findByRole("region", { name: /Itineraries/ });
    await user.selectOptions(screen.getByLabelText("Route"), "MCO-LAS");
    await waitFor(() => {
      const ids = within(list())
        .getAllByRole("button")
        .map((b) => b.getAttribute("data-itinerary"));
      expect(ids.sort()).toEqual(
        route("MCO-LAS")
          .itineraries.map((i) => i.itinerary_id)
          .sort(),
      );
    });
    expect(window.location.search).toBe("?route=MCO-LAS");
    expect(screen.getByText("Select an itinerary to see how often it worked.")).toBeInTheDocument();
  });
});

describe("the address (US2)", () => {
  it("opens a linked route and itinerary", async () => {
    const it = route("MCO-LAS").itineraries[2];
    if (!it) throw new Error("fixture");
    open(`?route=MCO-LAS&itinerary=${encodeURIComponent(it.itinerary_id)}`);
    const card = await screen.findByRole("article");
    expect(card).toHaveAttribute("aria-labelledby", "detail-itinerary");
    expect(
      list().querySelector(`[data-itinerary="${CSS.escape(it.itinerary_id)}"]`),
    ).toHaveAttribute("aria-pressed", "true");
  });

  it("falls back to the default view with a note for an unknown route", async () => {
    open("?route=XXX-YYY");
    expect(await screen.findByRole("status")).toHaveTextContent("was not found");
    expect(window.location.search).toBe("");
  });

  it("drops an itinerary that is not on the route, with a note", async () => {
    open("?route=MCO-LAS&itinerary=nope");
    expect(await screen.findByText(/linked itinerary was not found/)).toBeInTheDocument();
    expect(window.location.search).toBe("?route=MCO-LAS");
  });

  it("goes back to the previous selection", async () => {
    const user = userEvent.setup();
    open("");
    await screen.findByRole("region", { name: /Itineraries/ });
    const [first] = within(list()).getAllByRole("button");
    if (!first) throw new Error("no itinerary");
    await user.click(first);
    expect(first).toHaveAttribute("aria-pressed", "true");
    await act(async () => {
      window.history.back();
      await new Promise((resolve) => setTimeout(resolve, 50));
    });
    await waitFor(() => {
      expect(first).toHaveAttribute("aria-pressed", "false");
    });
  });
});
