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

/** The two cards' border widths, after serving a changed landing file. */
async function borders(
  page: import("@playwright/test").Page,
  edit: (landing: ReturnType<typeof committedLanding>) => void,
): Promise<string[]> {
  const landing = committedLanding();
  edit(landing);
  await page.route("**/data/showcase/landing.json", (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(landing) }),
  );
  await openLanding(page, 1280);
  return page
    .getByRole("article")
    .evaluateAll((cards) => cards.map((c) => getComputedStyle(c).borderTopWidth));
}

test("only an itinerary that worked more often is set apart", async ({ page }) => {
  expect(await borders(page, () => undefined)).toEqual(["2px", "1px"]);
});

test("similar itineraries get the same border (FR-002, FR-005)", async ({ page }) => {
  const widths = await borders(page, (landing) => {
    for (const c of landing.comparisons) {
      c.ci_low = -0.01;
      c.ci_high = 0.05;
      c.difference = 0.02;
    }
  });
  expect(widths).toEqual(["1px", "1px"]);
});

test("an itinerary below the minimum sample is not set apart or set below", async ({ page }) => {
  const widths = await borders(page, (landing) => {
    const b = landing.itineraries[1];
    if (!b) throw new Error("fixture has no second itinerary");
    b.result = {
      status: "insufficient_data",
      rate: null,
      paired_days: 12,
      count_feasible: 9,
      definition: "connection_feasibility",
    };
  });
  expect(widths).toEqual(["1px", "1px"]);
  await expect(page.locator("main")).toContainText("so the two are not compared");
});

test("text stays readable when the fonts fail to load", async ({ page }) => {
  await page.route("**/*.woff2", (route) => route.abort());
  await openLanding(page, 360);
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  await expect(page.getByRole("article").first()).toContainText("worked on 92% of 298 days");
});
