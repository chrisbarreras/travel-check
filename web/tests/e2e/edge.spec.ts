// Spec edge cases in a real browser: JavaScript disabled, and very long names on a 320 px
// screen.
import { committedLanding } from "../fixtures/committed";
import { expect, openLanding, test } from "../browser";

test.describe("with JavaScript disabled", () => {
  test.use({ javaScriptEnabled: false });

  test("shows the noscript message with its links", async ({ page }) => {
    await page.goto("./");
    const text = ((await page.locator("body").textContent()) ?? "").replace(/\s+/g, " ");
    expect(text).toContain("Travel Check needs JavaScript to show its example.");
    await expect(page.getByRole("link", { name: "source repository" })).toHaveAttribute(
      "href",
      "https://github.com/chrisbarreras/travel-check",
    );
    await expect(page.getByRole("link", { name: "methodology" })).toHaveAttribute(
      "href",
      "https://github.com/chrisbarreras/travel-check/blob/main/docs/methodology.md",
    );
  });
});

test("very long names wrap at 320 px without horizontal scroll", async ({ page }) => {
  const landing = committedLanding();
  for (const itinerary of landing.itineraries) {
    itinerary.airline_out = "ZZ"; // an unknown airline is shown by its code next to the name
    for (const leg of itinerary.find.legs) {
      leg.flight_number = `${leg.flight_number}${"0123456789".repeat(6)}`;
    }
  }
  await page.route("**/data/showcase/landing.json", (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(landing) }),
  );
  await openLanding(page, 320);
  await expect(page.getByRole("article").first()).toContainText("0123456789".repeat(6));
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
  );
  expect(overflow).toBeLessThanOrEqual(0);
});
