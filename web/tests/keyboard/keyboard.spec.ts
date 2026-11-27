// Scripted keyboard use (FR-010, SC-004): every control is reached in order, shows a visible
// focus outline, and works with the keyboard.
import { expect, openLanding, test } from "../browser";

/** Names of the focusable controls, in document order. */
async function focusableInOrder(page: import("@playwright/test").Page): Promise<string[]> {
  return page.evaluate(() =>
    [...document.querySelectorAll("a[href], summary, button, input, select, textarea")]
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
  const expected = await focusableInOrder(page);
  expect(expected.length).toBeGreaterThan(5);
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
