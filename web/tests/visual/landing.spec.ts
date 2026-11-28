// Visual references (FR-019). Runs only inside the pinned container (playwright.config.ts);
// references change only with `npm run test:visual:update` and a reviewed diff.
import { expect, openLanding, test } from "../browser";

for (const width of [360, 1280]) {
  test(`landing page at ${String(width)} px`, async ({ page }) => {
    await openLanding(page, width);
    await expect(page).toHaveScreenshot(`landing-${String(width)}.png`, { fullPage: true });
  });
}

test("error state at 360 px", async ({ page }) => {
  await page.route("**/data/showcase/landing.json", (route) =>
    route.fulfill({ status: 404, body: "not found" }),
  );
  await page.setViewportSize({ width: 360, height: 900 });
  await page.goto("./");
  await expect(page.getByText("This example could not be loaded")).toBeVisible();
  await page.evaluate(() => document.fonts.ready);
  await expect(page).toHaveScreenshot("error-360.png", { fullPage: true });
});

test("loading state at 360 px", async ({ page }) => {
  await page.route("**/data/showcase/landing.json", () => new Promise<void>(() => undefined));
  await page.setViewportSize({ width: 360, height: 900 });
  await page.goto("./");
  await expect(page.getByTestId("skeleton")).toBeVisible();
  await page.evaluate(() => document.fonts.ready);
  await expect(page).toHaveScreenshot("loading-360.png", { fullPage: true });
});
