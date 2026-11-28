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

for (const width of [360, 1280]) {
  test(`a route with a selected itinerary at ${String(width)} px has no violations`, async ({
    page,
  }) => {
    await page.setViewportSize({ width, height: 900 });
    await page.goto("./?route=MCO-LAS");
    const list = page.getByRole("region", { name: /Itineraries, by departure time/ });
    await list.getByRole("button").nth(2).click();
    await expect(page.getByRole("article")).toBeVisible();
    if (width < 768) await page.getByRole("button", { name: "Show map" }).click();
    await page.waitForFunction(() => window.__travelCheckMap?.loaded() === true);
    // Open every definition so their contents are checked too.
    await page.evaluate(() => {
      for (const d of document.querySelectorAll("details")) d.open = true;
    });
    const results = await new AxeBuilder({ page }).withTags(TAGS).analyze();
    expect(results.violations).toEqual([]);
  });
}

for (const width of [360, 1280]) {
  test(`a selected itinerary's slider and panels at ${String(width)} px have no violations`, async ({
    page,
  }) => {
    await page.setViewportSize({ width, height: 900 });
    await page.goto("./?route=LIT-LGA&itinerary=LIT-ATL-LGA%3ADL1238%2BDL1700&transfer=60");
    await expect(page.getByRole("slider")).toBeVisible();
    await page.evaluate(() => {
      for (const d of document.querySelectorAll("details")) d.open = true;
    });
    const results = await new AxeBuilder({ page }).withTags(TAGS).analyze();
    expect(results.violations).toEqual([]);
  });
}

test("the method view has no violations", async ({ page }) => {
  await page.goto("./?view=method");
  await expect(page.getByRole("heading", { name: "How the numbers work" })).toBeVisible();
  const results = await new AxeBuilder({ page }).withTags(TAGS).analyze();
  expect(results.violations).toEqual([]);
});
