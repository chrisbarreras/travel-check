// Shared Playwright fixture: no request may leave the local preview server (FR-022).
import { test as base, expect, type Page } from "@playwright/test";

export const test = base.extend({
  page: async ({ page, baseURL }, use) => {
    const allowed = new URL(baseURL ?? "http://127.0.0.1:4173/").origin;
    await page.route("**/*", (route) => {
      const url = new URL(route.request().url());
      return url.origin === allowed ? route.continue() : route.abort("blockedbyclient");
    });
    await use(page);
  },
});

export { expect };

/** Screen widths the layout is checked at (SC-009). */
export const WIDTHS = [320, 360, 768, 1280] as const;

/** Opens the page at a width and waits for the landing comparison. */
export async function openLanding(page: Page, width: number): Promise<void> {
  await page.setViewportSize({ width, height: 900 });
  await page.goto("./");
  await expect(page.getByRole("heading", { level: 2 })).toBeVisible();
  await page.evaluate(() => document.fonts.ready);
}
