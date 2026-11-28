// The slider and panels in a real browser (specs/005 SC-001, US1, US4).
import type { RouteFile } from "@contract";
import { committedFiles, committedIndex } from "../fixtures/committed";
import { expect, test } from "../browser";

const index = committedIndex();
const files = committedFiles();
const routes = index.routes.map((r) => files[`routes/${r.route_id}.json`] as RouteFile);

/** The shared rule, written out independently of the app's code. */
function expected(daily: RouteFile["itineraries"][number]["daily"], transfer: number): string {
  const threshold = transfer + index.assumptions.boarding_cutoff_min;
  const paired = daily.slack_min.length;
  const ok = daily.slack_min.filter(
    (s, i) => s !== null && s >= threshold && !"CD".includes(daily.outcome[i] ?? ""),
  ).length;
  if (paired < index.assumptions.min_sample_days)
    return `insufficient data (${String(paired)} days`;
  const percent = Math.floor((200 * ok + paired) / (2 * paired));
  return `worked on ${String(percent)}% of ${String(paired)} days`;
}

for (const route of routes) {
  test(`${route.route_id}: every itinerary at its default and two other transfer times`, async ({
    page,
  }) => {
    await page.setViewportSize({ width: 360, height: 800 }); // map hidden: faster
    for (const it of route.itineraries) {
      for (const transfer of [it.min_connection_min, 15, 90]) {
        await page.goto(
          `./?route=${route.route_id}&itinerary=${encodeURIComponent(it.itinerary_id)}&transfer=${String(transfer)}`,
        );
        await expect(page.locator(".slider-result")).toContainText(expected(it.daily, transfer));
      }
    }
  });
}

test("the slider works by keyboard and announces the result", async ({ page }) => {
  await page.goto("./?route=LIT-LGA&itinerary=LIT-ATL-LGA%3ADL1238%2BDL1700");
  const slider = page.getByRole("slider");
  await slider.focus();
  await page.keyboard.press("ArrowRight");
  await page.keyboard.press("ArrowRight");
  await expect(slider).toHaveValue("40");
  await expect(slider).toHaveAttribute("aria-valuetext", "40 minutes");
  await expect(page.locator(".slider-result")).toHaveAttribute("aria-live", "polite");
  await expect(page.locator(".slider-result")).toContainText("With 40 minutes");
  expect(new URL(page.url()).searchParams.get("transfer")).toBe("40");
});

test("Find this itinerary opens a search in a new tab, with the prices note", async ({ page }) => {
  await page.goto("./?route=LIT-LGA&itinerary=LIT-ATL-LGA%3ADL1238%2BDL1700");
  const link = page.getByRole("link", { name: /Find this itinerary/ });
  await expect(link).toHaveAttribute("target", "_blank");
  await expect(link).toHaveAttribute("rel", /noopener/);
  await expect(link).toHaveAttribute("href", /^https:\/\/www\.google\.com\/travel\/flights\?q=/);
  await expect(page.getByText("Prices come from that site")).toBeVisible();
});

test("How the numbers work is linked from the header and lists the definitions", async ({
  page,
}) => {
  await page.goto("./");
  await page.getByRole("link", { name: "How the numbers work" }).first().click();
  await expect(page.getByRole("heading", { name: "How the numbers work" })).toBeVisible();
  await expect(page.locator(".method-definitions dt")).toHaveCount(index.definitions.length);
  await page.getByRole("link", { name: "Back to the explorer" }).click();
  await expect(page.getByRole("region", { name: /^The example:/ })).toBeVisible();
});

test("a default or invalid transfer setting is cleared from the address (FR-003)", async ({
  page,
}) => {
  const base = "./?route=LIT-LGA&itinerary=LIT-ATL-LGA%3ADL1238%2BDL1700";
  for (const value of ["30", "62", "abc"]) {
    await page.goto(`${base}&transfer=${value}`);
    await expect(page.getByRole("slider")).toHaveValue("30");
    await expect.poll(() => new URL(page.url()).searchParams.has("transfer")).toBe(false);
  }
  await page.goto(`${base}&transfer=60`);
  await expect(page.getByRole("slider")).toHaveValue("60");
  expect(new URL(page.url()).searchParams.get("transfer")).toBe("60");
});
