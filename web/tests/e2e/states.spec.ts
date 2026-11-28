// Loading and error states in a real browser, by intercepting the data (US3).
import { expect, test } from "../browser";

test("a malformed landing file shows the plain error and no figures", async ({ page }) => {
  await page.route("**/data/showcase/landing.json", (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: '{"route_id": 1}' }),
  );
  await page.goto("./");
  await expect(page.getByText("This example could not be loaded")).toBeVisible();
  // Only the landing comparison fails; the route's list still works.
  await expect(page.locator(".detail-slot")).not.toContainText(/\d/);
  await expect(page.getByRole("region", { name: /Itineraries, by departure time/ })).toBeVisible();
});

test("a missing landing file shows the plain error", async ({ page }) => {
  await page.route("**/data/showcase/landing.json", (route) =>
    route.fulfill({ status: 404, body: "not found" }),
  );
  await page.goto("./");
  await expect(page.getByText("This example could not be loaded")).toBeVisible();
});

test("slow data shows the layout's shape without numbers", async ({ page }) => {
  let release: () => void = () => undefined;
  const held = new Promise<void>((resolve) => {
    release = resolve;
  });
  await page.route("**/data/showcase/landing.json", async (route) => {
    await held;
    await route.continue();
  });
  await page.goto("./");
  await expect(page.locator(".detail-slot").getByTestId("skeleton")).toBeVisible();
  await expect(page.locator(".detail-slot")).not.toContainText(/\d/);
  release();
  await expect(page.getByRole("region", { name: /^The example:/ })).toBeVisible();
});
