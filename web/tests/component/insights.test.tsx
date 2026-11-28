// The slider, risk visuals and insight panels against the published data (specs/005).
import { fireEvent, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { RouteFile, ShowcaseItinerary } from "@contract";
import { memorySource } from "../../src/data";
import {
  airlineName,
  duration,
  intervalText,
  localTime,
  percentOf,
  rateText,
} from "../../src/format";
import { findUrl } from "../../src/insights/find";
import { nameFromId } from "../../src/insights/InsightPanels";
import { meterDots } from "../../src/insights/meter";
import { monthBars } from "../../src/insights/months";
import { slackRate } from "../../src/insights/slackRate";
import { clone, committedFiles, committedIndex } from "../fixtures/committed";
import { renderApp } from "../fixtures/render";

const files = committedFiles();
const index = committedIndex();
const routes = index.routes.map((r) => files[`routes/${r.route_id}.json`] as RouteFile);
const period = "Jul 2024 – Jun 2025";

const link = (routeId: string, id: string, extra = "") =>
  `?route=${routeId}&itinerary=${encodeURIComponent(id)}${extra}`;

function open(search: string, source = memorySource(files)) {
  window.history.replaceState(null, "", `/${search}`);
  return renderApp(source);
}

afterEach(() => {
  window.history.replaceState(null, "", "/");
  vi.restoreAllMocks();
});

const panel = (name: string) => screen.getByRole("region", { name });

/** Every check of the panels' content against one itinerary's published data. */
function checkPanels(route: RouteFile, it: ShowcaseItinerary) {
  // Meter: filled dots follow the whole percent shown.
  const meter = document.querySelector(".slider .meter");
  if (it.result.status === "ok") {
    const percent = percentOf(it.result.count_feasible, it.result.paired_days);
    expect(meter?.getAttribute("data-filled")).toBe(String(meterDots(percent)));
  } else {
    expect(meter).toBeNull();
  }

  // Faster, just as reliable: content, direction of the difference, selectable only if shown.
  const faster = panel("Faster, just as reliable");
  if (it.faster_alternatives.length === 0) {
    expect(faster).toHaveTextContent("No faster itinerary on this route was as reliable.");
  }
  const onRoute = new Set(route.itineraries.map((i) => i.itinerary_id));
  for (const a of it.faster_alternatives) {
    const item = faster.querySelector(`[data-alternative="${CSS.escape(a.itinerary_id)}"]`);
    const text = item?.textContent ?? "";
    expect(text).toContain(`${String(a.minutes_saved)} min shorter`);
    expect(text).toContain(rateText(a.rate_other, period).text);
    expect(text).toContain(rateText(a.rate_this, period).text);
    expect(text).toContain(`The faster one minus this one: ${intervalText(a.ci_low, a.ci_high)}`);
    expect(text).toContain(`${String(a.shared_days)} days both flew`);
    const button = item?.querySelector("button");
    if (onRoute.has(a.itinerary_id)) expect(button).not.toBeNull();
    else {
      expect(button).toBeNull();
      expect(text).toContain(`${nameFromId(a.itinerary_id)} (not shown on this route)`);
    }
  }

  // Better connecting flight: suggestions only where marked, with their evidence.
  const better = panel("Better connecting flight");
  const marked = it.connecting_options.filter((o) => o.better);
  if (marked.length === 0) expect(better).toHaveTextContent("No other outbound flight");
  for (const o of marked) {
    expect(better).toHaveTextContent(
      `Leaving ${it.hub} at ${localTime(o.outbound_dep_local_min).text} local time: ${rateText(o.rate, period).text}`,
    );
    if (o.ci_low !== null && o.ci_high !== null) {
      expect(better).toHaveTextContent(intervalText(o.ci_low, o.ci_high));
    }
  }
  for (const o of it.connecting_options.filter((x) => !x.better)) {
    expect(better).toHaveTextContent(
      `${localTime(o.outbound_dep_local_min).text} (${rateText(o.rate, period).text})`,
    );
  }

  // Buffer you needed: needed against scheduled, the share, the sample.
  const buffer = panel("Buffer you needed");
  const b = it.buffer;
  if (b.needed_layover_min !== null && b.scheduled_at_least_share !== null) {
    expect(buffer).toHaveTextContent(`${String(b.operated_days)} operated days`);
    expect(buffer).toHaveTextContent(`needed to be at least ${duration(b.needed_layover_min)}`);
    expect(buffer).toHaveTextContent(`median is ${duration(b.actual_layover_min)}`);
    expect(buffer).toHaveTextContent(
      `${String(Math.round(b.scheduled_at_least_share * 100))}% of those days`,
    );
  }

  // Why it didn't work: counts, sample, setting, and the dominant type's sentence.
  const why = panel("Why it didn't work");
  expect(why).toHaveTextContent(`Too little time: ${String(it.failures.too_little_time)}`);
  expect(why).toHaveTextContent(`A leg was cancelled: ${String(it.failures.cancelled)}`);
  expect(why).toHaveTextContent(`A leg was diverted: ${String(it.failures.diverted)}`);
  expect(why).toHaveTextContent(`of ${String(it.result.paired_days)} days, ${period}`);
  expect(why).toHaveTextContent(`${String(it.min_connection_min)}-minute minimum connection time`);
  const sentence = {
    too_little_time: "A longer scheduled layover",
    cancelled: "A longer layover would not have helped",
    diverted: "Diversions are rare",
    none: "Every counted day worked",
  }[it.failures.dominant];
  expect(why).toHaveTextContent(sentence);

  // By month: values, note markers, and each note's dates, text and source.
  const months = panel("By month");
  const bars = monthBars(it.monthly, route.disruption_notes);
  const items = within(months)
    .getAllByRole("listitem")
    .filter((li) => li.classList.contains("month"));
  expect(items.map((li) => li.querySelector(".month-value")?.textContent)).toEqual(
    bars.map((bar) =>
      bar.kind === "ok"
        ? `${String(bar.percent)}%`
        : bar.kind === "none"
          ? "–"
          : `${String(bar.days)} d`,
    ),
  );
  items.forEach((li, i) => {
    expect(li.querySelector("sup") !== null).toBe((bars[i]?.notes.length ?? 0) > 0);
  });
  for (const note of route.disruption_notes.filter((n) =>
    bars.some((bar) => bar.notes.includes(n.note_id)),
  )) {
    expect(months).toHaveTextContent(`${note.start} to ${note.end}: ${note.text}`);
    const source = within(months)
      .getAllByRole("link", { name: "Source" })
      .map((a) => a.getAttribute("href"));
    expect(source).toContain(note.source_url);
  }

  // About this itinerary: connection share, every schedule change, sold passengers.
  const about = panel("About this itinerary");
  const w = it.schedule_warnings;
  expect(about).toHaveTextContent(
    `scheduled to connect on ${String(w.connecting_days)} of ${String(w.eligible_days)} days`,
  );
  if (w.changes.length === 0) expect(about).toHaveTextContent("No lasting schedule changes");
  for (const c of w.changes) {
    expect(about).toHaveTextContent(
      `${c.date}: the ${c.leg} flight moved from ${localTime(c.from_local_min).text} to ${localTime(c.to_local_min).text} local time.`,
    );
  }
  expect(about).toHaveTextContent(`${String(it.sold.passengers)} sampled passengers`);

  // Find link.
  const names = [...new Set([it.airline, it.airline_out])].map(airlineName);
  expect(screen.getByRole("link", { name: /Find this itinerary/ })).toHaveAttribute(
    "href",
    findUrl(it.find, names),
  );
}

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

  it("defaults to a partner itinerary's own minimum, and shows no meter below the minimum sample", async () => {
    const changed = clone(route);
    const target = changed.itineraries.find((i) => i.itinerary_id === it_.itinerary_id);
    if (!target) throw new Error("fixture");
    target.min_connection_min = 45;
    // Twelve days: below the 30-day minimum, so the published status is insufficient.
    target.daily = {
      day_offset: target.daily.day_offset.slice(0, 12),
      outcome: target.daily.outcome.slice(0, 12),
      slack_min: target.daily.slack_min.slice(0, 12),
    };
    const fed = slackRate(target.daily, 45, 15, 30);
    target.result = {
      ...fed,
      definition: "connection_feasibility",
      status: "insufficient_data",
      rate: null,
    };
    changed.comparisons = changed.comparisons.filter(
      (c) => c.itinerary_a !== target.itinerary_id && c.itinerary_b !== target.itinerary_id,
    );
    open(
      link("LIT-LGA", target.itinerary_id),
      memorySource({ ...files, "routes/LIT-LGA.json": changed }),
    );
    const slider = await screen.findByRole("slider");
    expect(slider).toHaveValue("45");
    const result = document.querySelector(".slider-result");
    expect(result).toHaveTextContent("insufficient data (12 days");
    expect(result?.querySelector(".meter")).toBeNull();
    expect(result?.textContent).not.toMatch(/\d+%/);
  });
});

describe("visuals and panels match the published data on every itinerary (SC-003)", () => {
  it.each(routes.map((r) => [r.route_id, r] as const))(
    "%s",
    async (routeId, route) => {
      for (const it of route.itineraries) {
        const { unmount } = open(link(routeId, it.itinerary_id));
        await screen.findByRole("slider");
        checkPanels(route, it);
        unmount();
      }
    },
    120_000,
  );
});

describe("choosing a faster alternative (US3 AS1)", () => {
  it("selects every selectable alternative on the same route", async () => {
    const user = userEvent.setup();
    for (const route of routes) {
      const onRoute = new Set(route.itineraries.map((i) => i.itinerary_id));
      for (const it of route.itineraries) {
        for (const a of it.faster_alternatives.filter((x) => onRoute.has(x.itinerary_id))) {
          const { unmount } = open(link(route.route_id, it.itinerary_id));
          await screen.findByRole("slider");
          const item = panel("Faster, just as reliable").querySelector(
            `[data-alternative="${CSS.escape(a.itinerary_id)}"]`,
          );
          const button = item?.querySelector("button");
          if (!button) throw new Error(`no button for ${a.itinerary_id}`);
          await user.click(button);
          expect(new URLSearchParams(window.location.search).get("itinerary")).toBe(a.itinerary_id);
          expect(new URLSearchParams(window.location.search).get("route")).toBe(route.route_id);
          expect(screen.queryByText(/was not found/)).not.toBeInTheDocument();
          unmount();
        }
      }
    }
  }, 120_000);
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
