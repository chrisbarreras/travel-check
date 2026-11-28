// Automated accessibility rules at WCAG 2.2 AA (FR-020, SC-004).
import AxeBuilder from "@axe-core/playwright";
import { expect, openLanding, test } from "../browser";

const TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"];

for (const width of [360, 1280]) {
  test(`landing page at ${String(width)} px has no violations`, async ({ page }) => {
    await openLanding(page, width);
    // Open every definition so their contents are checked too.
    for (const summary of await page.locator("details > summary").all()) await summary.click();
    const results = await new AxeBuilder({ page }).withTags(TAGS).analyze();
    expect(results.violations).toEqual([]);
  });
}

test("error state has no violations", async ({ page }) => {
  await page.route("**/data/showcase/landing.json", (route) =>
    route.fulfill({ status: 404, body: "not found" }),
  );
  await page.goto("./");
  await expect(page.getByText("This example could not be loaded")).toBeVisible();
  const results = await new AxeBuilder({ page }).withTags(TAGS).analyze();
  expect(results.violations).toEqual([]);
});
