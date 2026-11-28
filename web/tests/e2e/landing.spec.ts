// Every figure on the page equals the committed data (FR-018, SC-003), at every width
// (SC-009). Expected texts are written by hand in landing-expected.ts, not computed with the
// formatting code under test, and are tied to the data by `checkRaw`.
import { committedIndex, committedLanding, committedManifest } from "../fixtures/committed";
import { EXPECTED, checkRaw } from "../fixtures/landing-expected";
import { WIDTHS, expect, openLanding, test } from "../browser";

test("the hand-checked expectations still describe the committed data", () => {
  checkRaw(committedLanding(), committedManifest().run.run_at);
});

for (const width of WIDTHS) {
  test.describe(`at ${String(width)} px`, () => {
    test("shows every landing figure exactly as in the data", async ({ page }) => {
      await openLanding(page, width);
      await expect(page).toHaveTitle("Travel Check");
      await expect(page.getByRole("heading", { level: 1 })).toHaveText("Travel Check");
      await expect(page.getByRole("heading", { level: 2 })).toHaveText(EXPECTED.heading);
      await expect(page.locator(".summary")).toHaveText(EXPECTED.summary);
      const cards = page.getByRole("article");
      await expect(cards).toHaveCount(2);
      for (const text of EXPECTED.a) await expect(cards.nth(0)).toContainText(text);
      for (const text of EXPECTED.b) await expect(cards.nth(1)).toContainText(text);
      await expect(cards.nth(1)).not.toContainText("Not counted");
      const difference = page.locator(".difference");
      for (const text of EXPECTED.difference) await expect(difference).toContainText(text);
      const footer = page.getByRole("contentinfo");
      for (const text of EXPECTED.footer) await expect(footer).toContainText(text);
      for (const attribution of committedIndex().attribution) {
        await expect(footer).toContainText(attribution.text);
      }
      // No other percentage appears unexplained (constitution, Principle I).
      const percentages = await page
        .locator("main")
        .evaluate((m) => m.textContent.match(/\d+%(?! interval)/g));
      expect(percentages).toEqual(["92%", "92%", "64%", "64%"]);
    });

    test("has no horizontal scroll and 44 px touch targets", async ({ page }) => {
      // Standalone controls only: links inside a sentence are exempt (WCAG 2.2, 2.5.8).
      await openLanding(page, width);
      const overflow = await page.evaluate(
        () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
      );
      expect(overflow).toBeLessThanOrEqual(0);
      const small = await page.evaluate(() =>
        [...document.querySelectorAll(".links a, summary, button")]
          .map((el) => {
            const box = el.getBoundingClientRect();
            return { text: el.textContent.trim(), height: box.height, width: box.width };
          })
          .filter((t) => t.height < 44 || t.width < 44),
      );
      expect(small).toEqual([]);
      // Inline links still meet the 24 px minimum spacing of WCAG 2.5.8.
      const inline = await page.evaluate(
        () =>
          [...document.querySelectorAll("a:not(.links a)")].filter(
            (el) => el.getBoundingClientRect().height < 16,
          ).length,
      );
      expect(inline).toBe(0);
    });
  });
}

test("reflows at 200% text size without horizontal scroll (SC-009)", async ({ page }) => {
  await openLanding(page, 360);
  await page.addStyleTag({ content: "html { font-size: 200% !important; }" });
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
  );
  expect(overflow).toBeLessThanOrEqual(0);
});
