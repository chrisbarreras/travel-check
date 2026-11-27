// Cross-checks the schema cannot express (contracts/data-access.md, Cross-checks).
import type { RouteFile, ShowcaseIndex, ShowcaseManifest } from "@contract";
import { builtDate } from "../format/time";
import type { LandingView, Result } from "./types";

/** The manifest types `run` loosely, so the timestamp is checked by parsing it as displayed. */
function isTimestamp(text: string): boolean {
  try {
    builtDate(text);
    return true;
  } catch {
    return false;
  }
}

/** Definitions the landing page shows; a figure is never shown without its definition (I). */
export const REQUIRED_DEFINITIONS = [
  "connection_feasibility",
  "paired_days",
  "comparison_difference",
  "insufficient_data",
  "layover",
  "travel_time",
] as const;

/** `count / paired` rounded to 6 decimals, halves away from zero, as the pipeline stores it. */
function storedRate(count: number, paired: number): number {
  return Math.floor((2 * count * 1_000_000 + paired) / (2 * paired)) / 1_000_000;
}

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
  for (const itinerary of [a, b]) {
    const { count_feasible, paired_days, rate, status } = itinerary.result;
    if (count_feasible > paired_days) {
      return invalid(`${itinerary.itinerary_id}: more feasible days than paired days`);
    }
    // The page shows the rate from its counts; the published rate must agree with them.
    if (status === "ok" && (rate === null || rate !== storedRate(count_feasible, paired_days))) {
      return invalid(`${itinerary.itinerary_id}: rate ${String(rate)} disagrees with its counts`);
    }
  }
  // `itinerary_a` is the higher rate, so the difference and its interval read upwards.
  if (comparison.difference < 0 || comparison.ci_low > comparison.ci_high) {
    return invalid(`comparison ${comparison.comparison_id} is not ordered higher first`);
  }
  const missing = REQUIRED_DEFINITIONS.filter(
    (key) => !index.definitions.some((d) => d.key === key),
  );
  if (missing.length > 0) {
    return {
      ok: false,
      error: { kind: "invalid", file: "index.json", detail: `no definition ${missing.join(", ")}` },
    };
  }
  const builtAt = manifest.run.run_at;
  if (typeof builtAt !== "string" || !isTimestamp(builtAt)) {
    return {
      ok: false,
      error: { kind: "invalid", file: "manifest.json", detail: "run.run_at is not a timestamp" },
    };
  }
  return { ok: true, value: { index, landing, manifest, comparison, a, b, builtAt } };
}
