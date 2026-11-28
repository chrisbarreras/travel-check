// Scripted keyboard use (FR-010, SC-004): every control is reached in order, shows a visible
// focus outline, and works with the keyboard.
import { expect, openLanding, settle, test } from "../browser";

/** Names of the focusable controls, in document order. */
async function focusableInOrder(page: import("@playwright/test").Page): Promise<string[]> {
  return page.evaluate(() =>
    [
      ...document.querySelectorAll(
        'a[href], summary, button, input, select, textarea, [tabindex]:not([tabindex="-1"])',
      ),
    ]
      .filter((el) => el.checkVisibility())
      .map((el) => el.textContent.trim()),
  );
}

async function focused(page: import("@playwright/test").Page) {
  return page.evaluate(() => {
    const el = document.activeElement;
    if (!(el instanceof HTMLElement)) return null;
    const style = getComputedStyle(el);
    return {
      text: el.textContent.trim(),
      outline: style.outlineStyle === "none" ? 0 : parseFloat(style.outlineWidth),
    };
  });
}

test("Tab reaches every control in order with a visible 3 px outline", async ({ page }) => {
  await openLanding(page, 1280);
  // The map canvas becomes focusable once the map has loaded.
  await settle(page);
  // Open every definition (Enter and Space on a summary are tested below), so the links
  // inside them are walked too.
  await page.evaluate(() => {
    for (const d of document.querySelectorAll("details")) d.open = true;
  });
  await expect(page.locator("details:not([open])")).toHaveCount(0);
  const expected = await focusableInOrder(page);
  // Landing comparison 5, list 4, timeline 1.
  expect(expected.filter((name) => name.startsWith("How this is computed"))).toHaveLength(10);
  // Start the walk from the top of the document, as a keyboard user arriving on the page.
  await page.mouse.click(1, 1);
  const seen: string[] = [];
  for (let i = 0; i < expected.length; i++) {
    await page.keyboard.press("Tab");
    const now = await focused(page);
    expect(now, `step ${String(i)}`).not.toBeNull();
    expect(now?.outline, now?.text).toBeGreaterThanOrEqual(3);
    seen.push(now?.text ?? "");
  }
  expect(seen).toEqual(expected);

  // Shift+Tab walks back through the same order.
  const back: string[] = [];
  for (let i = 0; i < expected.length - 1; i++) {
    await page.keyboard.press("Shift+Tab");
    back.push((await focused(page))?.text ?? "");
  }
  expect(back).toEqual(expected.slice(0, -1).reverse());
});

test("Enter and Space open and close a definition", async ({ page }) => {
  await openLanding(page, 360);
  const summary = page.locator("details > summary").first();
  const details = page.locator("details").first();
  await summary.focus();
  await page.keyboard.press("Enter");
  await expect(details).toHaveAttribute("open", "");
  await page.keyboard.press("Space");
  await expect(details).not.toHaveAttribute("open", "");
});

test("the explorer works by keyboard alone (US3)", async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 900 });
  await page.goto("./");
  await expect(page.getByRole("region", { name: /^The example:/ })).toBeVisible();
  // Choose a route with the keyboard.
  await page.getByLabel("Route").focus();
  await page.keyboard.press("ArrowDown");
  const routeId = await page.getByLabel("Route").inputValue();
  await expect(page).toHaveURL(new RegExp(`route=${routeId}`));
  // Select from the list with Enter, then from the timeline with Space.
  const list = page.getByRole("region", { name: /Itineraries, by departure time/ });
  const card = list.getByRole("button").first();
  await card.focus();
  await page.keyboard.press("Enter");
  await expect(card).toHaveAttribute("aria-pressed", "true");
  const row = page.getByRole("region", { name: "Timeline" }).getByRole("button").last();
  await row.focus();
  await page.keyboard.press("Space");
  await expect(row).toHaveAttribute("aria-pressed", "true");
  const id = await row.getAttribute("data-itinerary");
  await expect(list.locator(`[data-itinerary="${String(id)}"]`)).toHaveAttribute(
    "aria-pressed",
    "true",
  );
  // The selection is announced.
  await expect(page.locator('[aria-live="polite"]')).toContainText("Selected:");
});
