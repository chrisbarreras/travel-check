// The explorer in a real browser (specs/004 US1, US2). Map tests read rendered features from
// the map instance, not pixels (constitution II); the basemap's tiles are blocked by the
// fixture, so only the background and the route layers draw.
import type { Page } from "@playwright/test";
import type { RouteFile } from "@contract";
import { byDeparture } from "../../src/format/timeline";
import { committedFiles, committedIndex } from "../fixtures/committed";
import { expect, test } from "../browser";

const index = committedIndex();
const files = committedFiles();
const routeFile = (id: string) => files[`routes/${id}.json`] as RouteFile;
const routeIds = index.routes.map((r) => r.route_id);

const list = (page: Page) => page.getByRole("region", { name: /Itineraries, by departure time/ });
const timeline = (page: Page) => page.getByRole("region", { name: "Timeline" });

async function waitForMap(page: Page): Promise<void> {
  await page.waitForFunction(() => {
    const map = window.__travelCheckMap;
    return map?.loaded() === true && map.isStyleLoaded();
  });
}

/** Itinerary ids drawn on the map: all paths, and the selected one. */
async function drawnPaths(page: Page): Promise<{ all: string[]; selected: string[] }> {
  return page.evaluate(() => {
    const map = window.__travelCheckMap;
    if (!map) throw new Error("no map");
    const ids = (layers: string[]) =>
      [
        ...new Set(
          map
            .queryRenderedFeatures({ layers })
            .map((f) => (f.properties as { itinerary_id: string }).itinerary_id),
        ),
      ].sort();
    return { all: ids(["paths-other", "paths-selected"]), selected: ids(["paths-selected"]) };
  });
}

test.describe("every showcase route (SC-001)", () => {
  for (const routeId of routeIds) {
    test(`${routeId}: the list, timeline and map show the route file's itineraries`, async ({
      page,
    }) => {
      await page.setViewportSize({ width: 1280, height: 900 });
      await page.goto(`./?route=${routeId}`);
      const expected = byDeparture(routeFile(routeId).itineraries).map((i) => i.itinerary_id);
      await expect(list(page).getByRole("button")).toHaveCount(expected.length);
      const listed = await list(page)
        .getByRole("button")
        .evaluateAll((els) => els.map((e) => e.getAttribute("data-itinerary")));
      expect(listed).toEqual(expected);
      const rows = await timeline(page)
        .getByRole("button")
        .evaluateAll((els) => els.map((e) => e.getAttribute("data-itinerary")));
      expect(rows).toEqual(expected);
      await waitForMap(page);
      const drawn = await drawnPaths(page);
      expect(drawn.all).toEqual([...expected].sort());
      expect(drawn.selected).toEqual([]);
    });
  }
});

test.describe("selection is shared by every view (SC-002)", () => {
  test("from the list, the timeline and the map", async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 900 });
    await page.goto("./?route=MCO-LAS");
    await waitForMap(page);
    const ordered = byDeparture(routeFile("MCO-LAS").itineraries);

    // From the list.
    const first = ordered[0];
    if (!first) throw new Error("no itinerary");
    await list(page).locator(`[data-itinerary="${first.itinerary_id}"]`).click();
    await expect(
      timeline(page).locator(`[data-itinerary="${first.itinerary_id}"]`),
    ).toHaveAttribute("aria-pressed", "true");
    await expect.poll(async () => (await drawnPaths(page)).selected).toEqual([first.itinerary_id]);
    await expect(page.getByRole("article")).toContainText(first.hub);

    // From the timeline.
    const last = ordered.at(-1);
    if (!last) throw new Error("no itinerary");
    await timeline(page).locator(`[data-itinerary="${last.itinerary_id}"]`).click();
    await expect(list(page).locator(`[data-itinerary="${last.itinerary_id}"]`)).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    await expect.poll(async () => (await drawnPaths(page)).selected).toEqual([last.itinerary_id]);

    // From the map: click a point on a path, away from the airport markers, and expect the
    // path the map reports under the pointer to be selected.
    const target = await page.evaluate((exclude) => {
      const map = window.__travelCheckMap;
      if (!map) throw new Error("no map");
      for (const feature of map.queryRenderedFeatures({ layers: ["paths-other"] })) {
        if (feature.geometry.type !== "LineString") continue;
        const coords = feature.geometry.coordinates;
        const p = map.project(coords[Math.floor(coords.length * 0.25)] as [number, number]);
        const under = map
          .queryRenderedFeatures([p.x, p.y], { layers: ["paths-hit"] })
          .map((f) => (f.properties as { itinerary_id: string }).itinerary_id);
        // The click picks the earliest id under the pointer unless the selection is there.
        const id = [...under].sort()[0];
        if (id && !under.includes(exclude)) {
          const box = map.getCanvas().getBoundingClientRect();
          return { id, x: box.left + p.x, y: box.top + p.y };
        }
      }
      throw new Error("no clickable path");
    }, last.itinerary_id);
    await page.mouse.click(target.x, target.y);
    await expect(list(page).locator(`[data-itinerary="${target.id}"]`)).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    await expect.poll(async () => (await drawnPaths(page)).selected).toEqual([target.id]);
  });
});

test.describe("links (US2, SC-003)", () => {
  for (const routeId of routeIds) {
    test(`${routeId}: every itinerary reopens from its address`, async ({ page }) => {
      await page.setViewportSize({ width: 360, height: 800 }); // map hidden: faster
      for (const it of routeFile(routeId).itineraries) {
        await page.goto(`./?route=${routeId}&itinerary=${encodeURIComponent(it.itinerary_id)}`);
        await expect(list(page).locator(`[data-itinerary="${it.itinerary_id}"]`)).toHaveAttribute(
          "aria-pressed",
          "true",
        );
        await expect(page.getByRole("status")).toHaveCount(0);
      }
    });
  }

  test("back and forward move between selections", async ({ page }) => {
    await page.goto("./?route=MCO-LAS");
    const [a, b] = byDeparture(routeFile("MCO-LAS").itineraries);
    if (!a || !b) throw new Error("fixture");
    await list(page).locator(`[data-itinerary="${a.itinerary_id}"]`).click();
    await list(page).locator(`[data-itinerary="${b.itinerary_id}"]`).click();
    await page.goBack();
    await expect(list(page).locator(`[data-itinerary="${a.itinerary_id}"]`)).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    await page.goBack();
    await expect(list(page).locator('[aria-pressed="true"]')).toHaveCount(0);
    await page.goForward();
    await expect(list(page).locator(`[data-itinerary="${a.itinerary_id}"]`)).toHaveAttribute(
      "aria-pressed",
      "true",
    );
  });

  test("an unknown route opens the default view with a note", async ({ page }) => {
    await page.goto("./?route=ZZZ-YYY&itinerary=x");
    await expect(page.getByRole("status")).toContainText("was not found");
    await expect(page.getByRole("region", { name: /^The example:/ })).toBeVisible();
    expect(new URL(page.url()).search).toBe("");
  });

  test("an itinerary not on the route opens the default view with a note", async ({ page }) => {
    await page.goto("./?route=MCO-LAS&itinerary=nope");
    await expect(page.getByRole("status")).toContainText("was not found");
    await expect(page.getByRole("region", { name: /^The example:/ })).toBeVisible();
    expect(new URL(page.url()).search).toBe("");
  });
});

test("when the map cannot load, the list and timeline still work (FR-012)", async ({ page }) => {
  await page.route("**/assets/MapView-*.js", (route) => route.abort());
  await page.setViewportSize({ width: 1280, height: 900 });
  await page.goto("./?route=MCO-LAS");
  await expect(page.getByText("The map could not be shown")).toBeVisible();
  const first = list(page).getByRole("button").first();
  await first.click();
  await expect(first).toHaveAttribute("aria-pressed", "true");
});

test("on a phone the map is hidden behind a labelled button (FR-013)", async ({ page }) => {
  await page.setViewportSize({ width: 360, height: 800 });
  await page.goto("./?route=MCO-LAS");
  const toggle = page.getByRole("button", { name: "Show map" });
  await expect(toggle).toHaveAttribute("aria-expanded", "false");
  await expect(page.locator("#map-area")).toBeHidden();
  await toggle.click();
  await expect(page.getByRole("button", { name: "Hide map" })).toHaveAttribute(
    "aria-expanded",
    "true",
  );
  await waitForMap(page);
  expect((await drawnPaths(page)).all.length).toBe(routeFile("MCO-LAS").itineraries.length);
  const order = await page.evaluate(() =>
    ["#route-picker", "#list-heading", "#timeline-heading", "#map-heading"].map(
      (s) => document.querySelector(s)?.getBoundingClientRect().top ?? -1,
    ),
  );
  expect([...order].sort((x, y) => x - y)).toEqual(order);
});

test("with the real basemap style but no tiles, the routes still draw (spec, Edge Cases)", async ({
  page,
}) => {
  // Serve the real style; its tile requests leave the local server and are blocked.
  await page.route("**/basemap-style.json", (route) => route.continue());
  await page.setViewportSize({ width: 1280, height: 900 });
  await page.goto("./?route=LAX-DCA");
  await waitForMap(page);
  expect((await drawnPaths(page)).all.length).toBe(routeFile("LAX-DCA").itineraries.length);
  await expect(page.locator(".maplibregl-ctrl-attrib")).toContainText("OpenStreetMap");
});

test.describe("every itinerary on every route selects in all views (SC-002)", () => {
  for (const routeId of routeIds) {
    test(routeId, async ({ page }) => {
      await page.setViewportSize({ width: 1280, height: 900 });
      await page.goto(`./?route=${routeId}`);
      await waitForMap(page);
      for (const it of routeFile(routeId).itineraries) {
        await list(page).locator(`[data-itinerary="${it.itinerary_id}"]`).click();
        await expect(
          timeline(page).locator(`[data-itinerary="${it.itinerary_id}"]`),
        ).toHaveAttribute("aria-pressed", "true");
        await expect.poll(async () => (await drawnPaths(page)).selected).toEqual([it.itinerary_id]);
      }
    });
  }
});

test.describe("map airports (US1-3)", () => {
  for (const routeId of routeIds) {
    test(`${routeId}: hubs are outlined circles with labels, and the ends are labelled`, async ({
      page,
    }) => {
      await page.setViewportSize({ width: 1280, height: 900 });
      await page.goto(`./?route=${routeId}`);
      await waitForMap(page);
      const [origin, dest] = routeId.split("-");
      const hubs = [...new Set(routeFile(routeId).itineraries.map((i) => i.hub))].sort();
      await expect(page.locator(".map-airport.origin .map-label")).toHaveText(String(origin));
      await expect(page.locator(".map-airport.destination .map-label")).toHaveText(String(dest));
      const hubLabels = await page.locator(".map-airport.hub .map-label").allTextContents();
      expect(hubLabels.sort()).toEqual(hubs);
      const border = await page
        .locator(".map-airport.hub .map-dot")
        .first()
        .evaluate((el) => getComputedStyle(el).borderTopWidth);
      expect(border).toBe("3px");
    });
  }
});

test("clicking the selected path keeps the selection, even where paths overlap", async ({
  page,
}) => {
  await page.setViewportSize({ width: 1280, height: 900 });
  await page.goto("./?route=MCO-LAS");
  await waitForMap(page);
  // Three itineraries share the path through DFW; select the last of them.
  const shared = routeFile("MCO-LAS").itineraries.filter((i) => i.hub === "DFW");
  const chosen = shared.at(-1);
  if (shared.length < 2 || !chosen) throw new Error("MCO-LAS needs a shared hub");
  await list(page).locator(`[data-itinerary="${chosen.itinerary_id}"]`).click();
  await expect.poll(async () => (await drawnPaths(page)).selected).toEqual([chosen.itinerary_id]);
  const point = await page.evaluate((id) => {
    const map = window.__travelCheckMap;
    if (!map) throw new Error("no map");
    const feature = map
      .queryRenderedFeatures({ layers: ["paths-selected"] })
      .find((f) => (f.properties as { itinerary_id: string }).itinerary_id === id);
    if (feature?.geometry.type !== "LineString") throw new Error("no selected path");
    const coords = feature.geometry.coordinates;
    const p = map.project(coords[Math.floor(coords.length * 0.25)] as [number, number]);
    const box = map.getCanvas().getBoundingClientRect();
    return { x: box.left + p.x, y: box.top + p.y };
  }, chosen.itinerary_id);
  await page.mouse.click(point.x, point.y);
  await page.waitForTimeout(200);
  await expect(list(page).locator(`[data-itinerary="${chosen.itinerary_id}"]`)).toHaveAttribute(
    "aria-pressed",
    "true",
  );
});
