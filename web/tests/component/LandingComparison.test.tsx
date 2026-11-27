import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import {
  airlineName,
  duration,
  excludedText,
  flightNumbers,
  intervalText,
  localTime,
  percentOf,
  periodText,
  points,
  signed,
} from "../../src/format";
import { committedIndex, committedLanding } from "../fixtures/committed";
import { renderApp } from "../fixtures/render";

const index = committedIndex();
const landing = committedLanding();
const comparison = landing.comparisons.find((c) => c.comparison_id === index.landing.comparison_id);
if (!comparison) throw new Error("committed landing file lacks its comparison");
const byId = (id: string) => {
  const found = landing.itineraries.find((i) => i.itinerary_id === id);
  if (!found) throw new Error(`missing ${id}`);
  return found;
};
const a = byId(comparison.itinerary_a);
const b = byId(comparison.itinerary_b);

async function ready() {
  renderApp();
  return screen.findByRole("heading", { level: 2 });
}

describe("the landing comparison, from the committed data (US1)", () => {
  it("names the app and the route with its period", async () => {
    const heading = await ready();
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("Travel Check");
    const origin = a.find.origin;
    const dest = a.find.dest;
    expect(heading).toHaveTextContent(`${origin} to ${dest}`);
    expect(document.body).toHaveTextContent(periodText(landing.period));
  });

  it("shows each itinerary's flights, times, layover and rate with its days", async () => {
    await ready();
    const cards = screen.getAllByRole("article");
    expect(cards).toHaveLength(2);
    for (const [card, itinerary] of [
      [cards[0], a],
      [cards[1], b],
    ] as const) {
      if (!card) throw new Error("missing card");
      const text = card.textContent;
      expect(text).toContain(`${airlineName(itinerary.airline)} via ${itinerary.hub}`);
      for (const number of flightNumbers(itinerary.find.legs).numbers)
        expect(text).toContain(number);
      expect(text).not.toMatch(/of days\)/);
      expect(text).toContain(localTime(itinerary.schedule.dep_local_min).text);
      expect(text).toContain(localTime(itinerary.schedule.arr_local_min).text);
      expect(text).toContain("local time");
      expect(text).toContain(duration(itinerary.schedule.layover_min));
      expect(text).toContain(duration(itinerary.schedule.travel_min));
      const percent = percentOf(itinerary.result.count_feasible, itinerary.result.paired_days);
      expect(text).toContain(
        `worked on ${String(percent)}% of ${String(itinerary.result.paired_days)} days`,
      );
      for (const line of excludedText(itinerary.excluded_days)) expect(text).toContain(line);
    }
  });

  it("puts the itinerary that worked more often first, and says so in words", async () => {
    await ready();
    const [first] = screen.getAllByRole("article");
    if (!first) throw new Error("missing card");
    expect(within(first).getByText(/worked more often/i)).toBeInTheDocument();
    expect(first).toHaveTextContent(`${airlineName(a.airline)} via ${a.hub}`);
  });

  it("states the difference in whole points with its interval and shared days", async () => {
    await ready();
    const text = document.body.textContent;
    expect(text).toContain(`${signed(points(comparison.difference))} points`);
    expect(text).toContain(intervalText(comparison.ci_low, comparison.ci_high));
    expect(text).toContain(`${String(comparison.shared_days)} days both flew`);
  });

  it("shows the published definitions verbatim", async () => {
    await ready();
    const user = userEvent.setup();
    for (const key of ["connection_feasibility", "paired_days", "comparison_difference"]) {
      const definition = index.definitions.find((d) => d.key === key);
      if (!definition) throw new Error(`no definition ${key}`);
      expect(screen.getByText(definition.text)).toBeInTheDocument();
    }
    const summaries = document.querySelectorAll("details > summary");
    expect(summaries.length).toBeGreaterThanOrEqual(3);
    const firstSummary = summaries[0];
    if (!(firstSummary instanceof HTMLElement)) throw new Error("no summary");
    await user.click(firstSummary);
    expect(firstSummary.parentElement).toHaveAttribute("open");
  });

  it("uses historical wording only", async () => {
    await ready();
    const text = document.body.textContent.toLowerCase();
    for (const word of [" chance", " will ", "probability", "likely", "guarantee"]) {
      expect(text, word).not.toContain(word);
    }
  });

  it("says this is an early version", async () => {
    await ready();
    expect(screen.getByText(/early version/i)).toBeInTheDocument();
  });
});
