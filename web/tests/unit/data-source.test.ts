import { describe, expect, it, vi } from "vitest";
import { buildLandingView, memorySource, staticSource } from "../../src/data";
import { REQUIRED_DEFINITIONS } from "../../src/data/landing";
import {
  clone,
  committedFiles,
  committedIndex,
  committedLanding,
  committedManifest,
} from "../fixtures/committed";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("memorySource with the committed files", () => {
  it("loads and validates the index, landing, manifest and every route", async () => {
    const source = memorySource(committedFiles());
    const index = await source.getIndex();
    expect(index.ok).toBe(true);
    expect((await source.getLanding()).ok).toBe(true);
    expect((await source.getManifest()).ok).toBe(true);
    if (!index.ok) return;
    for (const route of index.value.routes) {
      const result = await source.getRoute(route.route_id);
      expect(result.ok, route.route_id).toBe(true);
    }
  });
});

describe("rejection as a whole (contracts/data-access.md, Guarantees 1–2)", () => {
  it("rejects a missing required field", async () => {
    const files = committedFiles();
    const landing = clone(committedLanding()) as unknown as Record<string, unknown>;
    delete landing.comparisons;
    files["landing.json"] = landing;
    const result = await memorySource(files).getLanding();
    expect(result).toMatchObject({ ok: false, error: { kind: "invalid", file: "landing.json" } });
    expect("value" in result).toBe(false);
  });

  it("rejects an extra field", async () => {
    const files = committedFiles();
    files["index.json"] = { ...committedIndex(), surprise: true };
    expect(await memorySource(files).getIndex()).toMatchObject({
      ok: false,
      error: { kind: "invalid" },
    });
  });

  it("rejects a wrong type deep inside", async () => {
    const files = committedFiles();
    const landing = clone(committedLanding());
    const first = landing.itineraries[0];
    if (!first) throw new Error("fixture has no itinerary");
    (first.result as unknown as Record<string, unknown>).paired_days = "298";
    files["landing.json"] = landing;
    expect(await memorySource(files).getLanding()).toMatchObject({
      ok: false,
      error: { kind: "invalid" },
    });
  });

  it("returns not_found for a missing file", async () => {
    const files = committedFiles();
    delete files["manifest.json"];
    expect(await memorySource(files).getManifest()).toMatchObject({
      ok: false,
      error: { kind: "not_found", file: "manifest.json" },
    });
  });
});

describe("staticSource (with an injected fetch; no network)", () => {
  const files = committedFiles();
  const fetchFrom = (served: Record<string, unknown>) =>
    vi.fn((url: string) => {
      const path = url.replace(/^\/base\/data\/showcase\//, "");
      return Promise.resolve(
        path in served ? jsonResponse(served[path]) : new Response("not found", { status: 404 }),
      );
    });

  it("reads files below the base path", async () => {
    const fetchImpl = fetchFrom(files);
    const source = staticSource("/base/", fetchImpl);
    expect((await source.getIndex()).ok).toBe(true);
    expect(fetchImpl).toHaveBeenCalledWith("/base/data/showcase/index.json");
  });

  it("maps 404 to not_found and a failed request to network", async () => {
    expect(await staticSource("/base/", fetchFrom({})).getIndex()).toMatchObject({
      ok: false,
      error: { kind: "not_found" },
    });
    const failing = vi.fn(() => Promise.reject(new TypeError("Failed to fetch")));
    expect(await staticSource("/base/", failing).getIndex()).toMatchObject({
      ok: false,
      error: { kind: "network" },
    });
    const serverError = vi.fn(() => Promise.resolve(new Response("oops", { status: 500 })));
    expect(await staticSource("/base/", serverError).getIndex()).toMatchObject({
      ok: false,
      error: { kind: "network" },
    });
  });

  it("treats a body that is not JSON as invalid", async () => {
    const notJson = vi.fn(() => Promise.resolve(new Response("<html>", { status: 200 })));
    expect(await staticSource("/base/", notJson).getIndex()).toMatchObject({
      ok: false,
      error: { kind: "invalid" },
    });
  });

  it("fetches each file once per page load (Guarantee 4)", async () => {
    const fetchImpl = fetchFrom(files);
    const source = staticSource("/base/", fetchImpl);
    await Promise.all([source.getIndex(), source.getIndex(), source.getLanding()]);
    await source.getIndex();
    expect(fetchImpl).toHaveBeenCalledTimes(2);
  });

  it("fetches only routes listed in the index (Guarantee 3)", async () => {
    const fetchImpl = fetchFrom(files);
    const source = staticSource("/base/", fetchImpl);
    const unknown = await source.getRoute("../index");
    expect(unknown).toMatchObject({ ok: false, error: { kind: "not_found" } });
    expect(fetchImpl).toHaveBeenCalledTimes(1); // the index only
    const known = await source.getRoute("LIT-LGA");
    expect(known.ok).toBe(true);
    expect(fetchImpl).toHaveBeenLastCalledWith("/base/data/showcase/routes/LIT-LGA.json");
  });
});

describe("buildLandingView (contracts/data-access.md, Cross-checks)", () => {
  const index = committedIndex();
  const manifest = committedManifest();

  it("pairs the landing comparison with its two itineraries, higher rate first", () => {
    const view = buildLandingView(index, committedLanding(), manifest);
    expect(view.ok).toBe(true);
    if (!view.ok) return;
    expect(view.value.comparison.comparison_id).toBe(index.landing.comparison_id);
    expect(view.value.a.itinerary_id).toBe(view.value.comparison.itinerary_a);
    expect(view.value.b.itinerary_id).toBe(view.value.comparison.itinerary_b);
  });

  it("fails when the landing file is for another route", () => {
    const landing = { ...committedLanding(), route_id: "XXX-YYY" };
    expect(buildLandingView(index, landing, manifest)).toMatchObject({
      ok: false,
      error: { kind: "invalid" },
    });
  });

  it("fails when the landing comparison is missing", () => {
    const landing = { ...committedLanding(), comparisons: [] };
    expect(buildLandingView(index, landing, manifest)).toMatchObject({
      ok: false,
      error: { kind: "invalid" },
    });
  });

  it("fails when a build timestamp cannot be a real date", () => {
    const broken = { ...manifest, run: { ...manifest.run, run_at: "2026-13-45T00:00:00Z" } };
    expect(buildLandingView(index, committedLanding(), broken)).toMatchObject({
      ok: false,
      error: { kind: "invalid", file: "manifest.json" },
    });
  });

  it("fails when an itinerary has more feasible days than paired days", () => {
    const landing = clone(committedLanding());
    for (const itinerary of landing.itineraries) itinerary.result.count_feasible = 1000;
    expect(buildLandingView(index, landing, manifest)).toMatchObject({
      ok: false,
      error: { kind: "invalid" },
    });
  });

  it.each(REQUIRED_DEFINITIONS)("fails when the definition %s is missing", (key) => {
    const partial = { ...index, definitions: index.definitions.filter((d) => d.key !== key) };
    expect(buildLandingView(partial, committedLanding(), manifest)).toMatchObject({
      ok: false,
      error: { kind: "invalid", file: "index.json" },
    });
  });

  it("fails when a published rate disagrees with its counts", () => {
    const landing = clone(committedLanding());
    const first = landing.itineraries[0];
    if (!first) throw new Error("fixture has no itinerary");
    first.result.rate = 0.85;
    expect(buildLandingView(index, landing, manifest)).toMatchObject({
      ok: false,
      error: { kind: "invalid" },
    });
  });

  it("fails when a rate is published below the minimum sample", () => {
    const landing = clone(committedLanding());
    const first = landing.itineraries[0];
    if (!first) throw new Error("fixture has no itinerary");
    first.result = { ...first.result, paired_days: 12, count_feasible: 9, rate: 0.75 };
    expect(buildLandingView(index, landing, manifest)).toMatchObject({
      ok: false,
      error: { kind: "invalid" },
    });
  });

  it("accepts a rate within the pipeline's 1e-6 tolerance", () => {
    const landing = clone(committedLanding());
    const first = landing.itineraries[0];
    if (!first?.result.rate) throw new Error("fixture has no rate");
    first.result.rate += 0.0000005;
    expect(buildLandingView(index, landing, manifest).ok).toBe(true);
  });

  it("fails when the pair is not ordered higher first", () => {
    const landing = clone(committedLanding());
    for (const c of landing.comparisons) {
      c.difference = -0.2;
      c.ci_low = -0.3;
      c.ci_high = -0.1;
    }
    expect(buildLandingView(index, landing, manifest)).toMatchObject({
      ok: false,
      error: { kind: "invalid" },
    });
  });

  it("fails when the manifest has no build timestamp", () => {
    const broken = { ...manifest, run: { ...manifest.run, run_at: 42 } };
    expect(buildLandingView(index, committedLanding(), broken)).toMatchObject({
      ok: false,
      error: { kind: "invalid", file: "manifest.json" },
    });
  });

  it("fails when either itinerary is missing", () => {
    const landing = committedLanding();
    for (const keep of [0, 1]) {
      const partial = { ...landing, itineraries: landing.itineraries.slice(keep, keep + 1) };
      expect(buildLandingView(index, partial, manifest)).toMatchObject({
        ok: false,
        error: { kind: "invalid" },
      });
    }
  });
});
