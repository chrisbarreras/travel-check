// Visual references for the explorer (FR-015). Only inside the pinned container.
import { expect, settle, test } from "../browser";

test("a route with a selected itinerary at 1280 px", async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 900 });
  await page.goto("./?route=MCO-LAS");
  await page
    .getByRole("region", { name: /Itineraries, by departure time/ })
    .getByRole("button")
    .nth(2)
    .click();
  await settle(page);
  await expect(page).toHaveScreenshot("explorer-selected-1280.png", {
    fullPage: true,
    mask: [page.locator("#map-area")],
  });
});

test("a route at 360 px with the map shown", async ({ page }) => {
  await page.setViewportSize({ width: 360, height: 800 });
  await page.goto("./?route=HNL-BOS");
  await page.getByRole("button", { name: "Show map" }).click();
  await settle(page);
  await expect(page).toHaveScreenshot("explorer-map-360.png", {
    fullPage: true,
    mask: [page.locator("#map-area")],
  });
});
// The map's drawing is masked in screenshots: the software renderer can shift it by a pixel
// between runs, and the map is checked through its rendered features in tests/e2e/explorer.spec.ts.

test("a selected itinerary at 360 px", async ({ page }) => {
  await page.setViewportSize({ width: 360, height: 800 });
  await page.goto("./?route=LAX-DCA");
  await page
    .getByRole("region", { name: /Itineraries, by departure time/ })
    .getByRole("button")
    .first()
    .click();
  await settle(page);
  await expect(page).toHaveScreenshot("explorer-selected-360.png", { fullPage: true });
});

test("a route with nothing selected at 1280 px", async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 900 });
  await page.goto("./?route=SJC-ATL");
  await settle(page);
  await expect(page).toHaveScreenshot("explorer-route-1280.png", {
    fullPage: true,
    mask: [page.locator("#map-area")],
  });
});
