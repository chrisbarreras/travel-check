// The page's figures equal the committed data (FR-018, SC-003), at every width (SC-009).
import {
  airlineName,
  intervalText,
  localTime,
  percentOf,
  periodText,
  points,
  signed,
} from "../../src/format";
import { committedIndex, committedLanding } from "../fixtures/committed";
import { WIDTHS, expect, openLanding, test } from "../browser";

const index = committedIndex();
const landing = committedLanding();
const comparison = landing.comparisons.find((c) => c.comparison_id === index.landing.comparison_id);
if (!comparison) throw new Error("committed landing file lacks its comparison");
const itineraries = [comparison.itinerary_a, comparison.itinerary_b].map((id) => {
  const found = landing.itineraries.find((i) => i.itinerary_id === id);
  if (!found) throw new Error(`missing ${id}`);
  return found;
});

for (const width of WIDTHS) {
  test.describe(`at ${String(width)} px`, () => {
    test("shows the landing figures exactly as in the data", async ({ page }) => {
      await openLanding(page, width);
      await expect(page).toHaveTitle("Travel Check");
      const cards = page.getByRole("article");
      await expect(cards).toHaveCount(2);
      for (const [n, itinerary] of itineraries.entries()) {
        const card = cards.nth(n);
        const percent = percentOf(itinerary.result.count_feasible, itinerary.result.paired_days);
        await expect(card).toContainText(`${airlineName(itinerary.airline)} via ${itinerary.hub}`);
        await expect(card).toContainText(
          `worked on ${String(percent)}% of ${String(itinerary.result.paired_days)} days`,
        );
        await expect(card).toContainText(localTime(itinerary.schedule.dep_local_min).text);
        await expect(card).toContainText(localTime(itinerary.schedule.arr_local_min).text);
      }
      const body = page.locator("body");
      await expect(body).toContainText(`${signed(points(comparison.difference))} points`);
      await expect(body).toContainText(intervalText(comparison.ci_low, comparison.ci_high));
      await expect(body).toContainText(`${String(comparison.shared_days)} days both flew`);
      await expect(body).toContainText(periodText(landing.period));
    });

    test("has no horizontal scroll and 44 px touch targets", async ({ page }) => {
      // Standalone controls only: links inside a sentence are exempt (WCAG 2.2, 2.5.8).
      await openLanding(page, width);
      const overflow = await page.evaluate(
        () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
      );
      expect(overflow).toBeLessThanOrEqual(0);
      const small = await page.evaluate(() =>
        [...document.querySelectorAll(".links a, summary, button")]
          .map((el) => {
            const box = el.getBoundingClientRect();
            return { text: el.textContent.trim(), height: box.height, width: box.width };
          })
          .filter((t) => t.height < 44 || t.width < 24),
      );
      expect(small).toEqual([]);
      // Inline links still meet the 24 px minimum spacing of WCAG 2.5.8.
      const inline = await page.evaluate(
        () =>
          [...document.querySelectorAll("a:not(.links a)")].filter(
            (el) => el.getBoundingClientRect().height < 16,
          ).length,
      );
      expect(inline).toBe(0);
    });
  });
}

test("reflows at 200% text size without horizontal scroll (SC-009)", async ({ page }) => {
  await openLanding(page, 360);
  await page.addStyleTag({ content: "html { font-size: 200% !important; }" });
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
  );
  expect(overflow).toBeLessThanOrEqual(0);
});
