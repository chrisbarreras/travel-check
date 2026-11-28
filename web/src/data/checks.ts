// Cross-checks the schema cannot express, shared by the landing and route views
// (contracts/data-access.md, Cross-checks).
import type { ShowcaseComparison, ShowcaseIndex, ShowcaseItinerary } from "@contract";

/** `count / paired` rounded to 6 decimals, halves away from zero, as the pipeline stores it. */
function storedRate(count: number, paired: number): number {
  return Math.floor((2 * count * 1_000_000 + paired) / (2 * paired)) / 1_000_000;
}

/** Why an itinerary's figures can't be shown, or null when they can. */
export function itineraryProblem(
  index: ShowcaseIndex,
  itinerary: ShowcaseItinerary,
): string | null {
  const { count_feasible, paired_days, rate, status } = itinerary.result;
  if (count_feasible > paired_days) {
    return `${itinerary.itinerary_id}: more feasible days than paired days`;
  }
  // The page shows the rate from its counts; the published rate must agree with them, to
  // the pipeline's own tolerance (showcase/models.py, _RATE_TOLERANCE).
  if (
    status === "ok" &&
    (rate === null || Math.abs(rate - storedRate(count_feasible, paired_days)) > 1e-6)
  ) {
    return `${itinerary.itinerary_id}: rate ${String(rate)} disagrees with its counts`;
  }
  // A rate below the minimum sample is never shown (constitution, Principle I).
  if (status === "ok" && paired_days < index.assumptions.min_sample_days) {
    return `${itinerary.itinerary_id}: a rate from ${String(paired_days)} days`;
  }
  return null;
}

/** `itinerary_a` is the higher rate, so the difference and its interval read upwards. */
export function comparisonProblem(comparison: ShowcaseComparison): string | null {
  return comparison.difference < 0 || comparison.ci_low > comparison.ci_high
    ? `comparison ${comparison.comparison_id} is not ordered higher first`
    : null;
}

/** Definition keys missing from the index. */
export function missingDefinitions(index: ShowcaseIndex, keys: readonly string[]): string[] {
  return keys.filter((key) => !index.definitions.some((d) => d.key === key));
}
