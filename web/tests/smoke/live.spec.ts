// The deployed page shows the landing figures (FR-025). Expected texts are the hand-checked
// ones of landing-expected.ts, not computed with the code under test.
import { expect, test } from "@playwright/test";
import { EXPECTED } from "../fixtures/landing-expected";

test("the live site shows the landing comparison", async ({ page }) => {
  await page.goto("./");
  await expect(page).toHaveTitle("Travel Check");
  await expect(page.getByRole("heading", { level: 2 })).toHaveText(EXPECTED.heading, {
    timeout: 30_000,
  });
  const cards = page.getByRole("article");
  for (const text of EXPECTED.a) await expect(cards.nth(0)).toContainText(text);
  for (const text of EXPECTED.b) await expect(cards.nth(1)).toContainText(text);
  for (const text of EXPECTED.difference)
    await expect(page.locator(".difference")).toContainText(text);
});
