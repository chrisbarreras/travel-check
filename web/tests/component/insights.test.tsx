// The slider, risk visuals and insight panels against the published data (specs/005).
import { fireEvent, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { RouteFile } from "@contract";
import { airlineName, percentOf, rateText } from "../../src/format";
import { findUrl } from "../../src/insights/find";
import { meterDots } from "../../src/insights/meter";
import { monthBars } from "../../src/insights/months";
import { slackRate } from "../../src/insights/slackRate";
import { committedFiles, committedIndex } from "../fixtures/committed";
import { renderApp } from "../fixtures/render";

const files = committedFiles();
const index = committedIndex();
const routes = index.routes.map((r) => files[`routes/${r.route_id}.json`] as RouteFile);
const period = "Jul 2024 – Jun 2025";

function open(search: string) {
  window.history.replaceState(null, "", `/${search}`);
  renderApp();
}

const link = (routeId: string, id: string, extra = "") =>
  `?route=${routeId}&itinerary=${encodeURIComponent(id)}${extra}`;

afterEach(() => {
  window.history.replaceState(null, "", "/");
  vi.restoreAllMocks();
});

describe("the transfer-time slider (US1)", () => {
  const route = routes.find((r) => r.route_id === "LIT-LGA");
  const it_ = route?.itineraries.find((i) => i.itinerary_id === "LIT-ATL-LGA:DL1238+DL1700");
  if (!route || !it_) throw new Error("fixture");

  it("shows the published rate at the itinerary's default", async () => {
    open(link("LIT-LGA", it_.itinerary_id));
    const slider = await screen.findByRole("slider");
    expect(slider).toHaveValue(String(it_.min_connection_min));
    expect(screen.getByText(/With \d+ minutes:/)).toHaveTextContent(
      `${rateText(it_.result, period).text} (the published figure)`,
    );
  });

  it("recomputes from daily slack, and keeps the setting in the address without history", async () => {
    const push = vi.spyOn(window.history, "pushState");
    open(link("LIT-LGA", it_.itinerary_id));
    const slider = await screen.findByRole("slider");
    fireEvent.change(slider, { target: { value: "60" } });
    const expected = slackRate(it_.daily, 60, 15, 30);
    expect(screen.getByText(/With 60 minutes:/)).toHaveTextContent(
      `worked on ${String(percentOf(expected.count_feasible, expected.paired_days))}% of ${String(expected.paired_days)} days`,
    );
    expect(window.location.search).toContain("transfer=60");
    expect(push).not.toHaveBeenCalled();
    fireEvent.change(slider, { target: { value: String(it_.min_connection_min) } });
    expect(window.location.search).not.toContain("transfer");
  });

  it("opens a linked setting", async () => {
    open(link("LIT-LGA", it_.itinerary_id, "&transfer=90"));
    expect(await screen.findByRole("slider")).toHaveValue("90");
  });
});

describe("visuals and panels match the published data on every itinerary (SC-003)", () => {
  it.each(routes.map((r) => [r.route_id, r] as const))(
    "%s",
    async (routeId, route) => {
      for (const it of route.itineraries) {
        const { unmount } = (() => {
          window.history.replaceState(null, "", `/${link(routeId, it.itinerary_id)}`);
          return renderApp();
        })();
        await screen.findByRole("slider");
        // Meter: filled dots equal the rate to the nearest 10%.
        const meter = document.querySelector(".slider .meter");
        if (it.result.rate !== null) {
          expect(meter?.getAttribute("data-filled")).toBe(String(meterDots(it.result.rate)));
        } else {
          expect(meter).toBeNull();
        }
        // Failure bar counts.
        const why = screen.getByRole("region", { name: "Why it didn't work" });
        expect(why).toHaveTextContent(`Too little time: ${String(it.failures.too_little_time)}`);
        expect(why).toHaveTextContent(`A leg was cancelled: ${String(it.failures.cancelled)}`);
        expect(why).toHaveTextContent(`A leg was diverted: ${String(it.failures.diverted)}`);
        // Monthly bars.
        const months = screen.getByRole("region", { name: "By month" });
        const bars = monthBars(it.monthly, route.disruption_notes);
        const values = within(months)
          .getAllByRole("listitem")
          .filter((li) => li.classList.contains("month"))
          .map((li) => li.querySelector(".month-value")?.textContent);
        expect(values).toEqual(
          bars.map((b) =>
            b.kind === "ok"
              ? `${String(b.percent)}%`
              : b.kind === "none"
                ? "–"
                : `${String(b.days)} d`,
          ),
        );
        // Suggestions only where the data marks them.
        const faster = screen.getByRole("region", { name: "Faster, just as reliable" });
        expect(within(faster).queryAllByRole("button")).toHaveLength(it.faster_alternatives.length);
        const better = screen.getByRole("region", { name: "Better connecting flight" });
        const betterCount = it.connecting_options.filter((o) => o.better).length;
        if (betterCount === 0) expect(better).toHaveTextContent("No other outbound flight");
        else expect(within(better).getAllByRole("listitem")).toHaveLength(betterCount);
        // Find link.
        const names = [...new Set([it.airline, it.airline_out])].map(airlineName);
        expect(screen.getByRole("link", { name: /Find this itinerary/ })).toHaveAttribute(
          "href",
          findUrl(it.find, names),
        );
        unmount();
      }
    },
    60_000,
  );
});

describe("How the numbers work (FR-010)", () => {
  it("lists every published definition verbatim", async () => {
    open("?view=method");
    expect(
      await screen.findByRole("heading", { name: "How the numbers work" }),
    ).toBeInTheDocument();
    for (const d of index.definitions) expect(screen.getByText(d.text)).toBeInTheDocument();
  });
});
