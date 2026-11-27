// Cross-checks the schema cannot express (contracts/data-access.md, Cross-checks).
import type { RouteFile, ShowcaseIndex, ShowcaseManifest } from "@contract";
import type { LandingView, Result } from "./types";

function invalid(detail: string): Result<LandingView> {
  return { ok: false, error: { kind: "invalid", file: "landing.json", detail } };
}

export function buildLandingView(
  index: ShowcaseIndex,
  landing: RouteFile,
  manifest: ShowcaseManifest,
): Result<LandingView> {
  if (landing.route_id !== index.landing.route_id) {
    return invalid(`route ${landing.route_id} is not the index's ${index.landing.route_id}`);
  }
  const comparison = landing.comparisons.find(
    (c) => c.comparison_id === index.landing.comparison_id,
  );
  if (!comparison) return invalid(`no comparison ${index.landing.comparison_id}`);
  const a = landing.itineraries.find((i) => i.itinerary_id === comparison.itinerary_a);
  const b = landing.itineraries.find((i) => i.itinerary_id === comparison.itinerary_b);
  if (!a || !b) return invalid(`comparison ${comparison.comparison_id} lacks an itinerary`);
  const builtAt = manifest.run.run_at;
  if (typeof builtAt !== "string" || !/^\d{4}-\d{2}-\d{2}T/.test(builtAt)) {
    return {
      ok: false,
      error: { kind: "invalid", file: "manifest.json", detail: "run.run_at is not a timestamp" },
    };
  }
  return { ok: true, value: { index, landing, manifest, comparison, a, b, builtAt } };
}
