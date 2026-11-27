// The deployed page shows the landing figures of the data it was built with (FR-025).
import { expect, test } from "@playwright/test";
import { percentOf } from "../../src/format";
import { committedIndex, committedLanding } from "../fixtures/committed";

const index = committedIndex();
const landing = committedLanding();
const comparison = landing.comparisons.find((c) => c.comparison_id === index.landing.comparison_id);

test("the live site shows the landing comparison", async ({ page }) => {
  if (!comparison) throw new Error("committed landing file lacks its comparison");
  await page.goto("./");
  await expect(page).toHaveTitle("Travel Check");
  await expect(page.getByRole("heading", { level: 2 })).toBeVisible({ timeout: 30_000 });
  for (const id of [comparison.itinerary_a, comparison.itinerary_b]) {
    const itinerary = landing.itineraries.find((i) => i.itinerary_id === id);
    if (!itinerary) throw new Error(`missing ${id}`);
    const percent = percentOf(itinerary.result.count_feasible, itinerary.result.paired_days);
    await expect(page.locator("body")).toContainText(
      `worked on ${String(percent)}% of ${String(itinerary.result.paired_days)} days`,
    );
  }
});
