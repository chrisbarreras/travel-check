// Shared Playwright fixture: no request may leave the local preview server (FR-022).
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { test as base, expect, type Page } from "@playwright/test";

/** The local blank basemap every test uses instead of the real style (FR-016, research R5). */
const BLANK_STYLE = readFileSync(
  join(process.cwd(), "tests", "fixtures", "blank-style.json"),
  "utf8",
);

export const test = base.extend({
  page: async ({ page, baseURL }, use) => {
    const allowed = new URL(baseURL ?? "http://127.0.0.1:4173/").origin;
    // Lets the map tests read rendered features (research R6).
    await page.addInitScript(() => {
      window.__travelCheckTest = true;
    });
    await page.route("**/*", (route) => {
      const url = new URL(route.request().url());
      return url.origin === allowed ? route.continue() : route.abort("blockedbyclient");
    });
    await page.route("**/basemap-style.json", (route) =>
      route.fulfill({ status: 200, contentType: "application/json", body: BLANK_STYLE }),
    );
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
  await expect(landing(page)).toBeVisible();
  await page.evaluate(() => document.fonts.ready);
}

/** The landing comparison's region. */
export function landing(page: Page) {
  return page.getByRole("region", { name: /^The example:/ });
}

/**
 * Waits until fonts are loaded and, if a map is on the page, until it has finished drawing,
 * so screenshots are taken of a still page.
 */
export async function settle(page: Page): Promise<void> {
  await page.evaluate(() => document.fonts.ready);
  if ((await page.locator("#map-area:not([hidden])").count()) > 0) {
    await page.waitForFunction(() => {
      const map = window.__travelCheckMap;
      return map?.loaded() === true && !map.isMoving();
    });
    await page.evaluate(
      () =>
        new Promise<void>((resolve) => {
          const map = window.__travelCheckMap;
          if (!map) {
            resolve();
            return;
          }
          void map.once("idle", () => {
            resolve();
          });
          map.triggerRepaint();
        }),
    );
  }
}
