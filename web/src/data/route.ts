// A showcase route, validated and cross-checked for the explorer (FR-011).
import type { AirportInfo, RouteFile, ShowcaseIndex } from "@contract";
import { byDeparture } from "../format/timeline";
import { comparisonProblem, itineraryProblem, missingDefinitions } from "./checks";
import type { Result, RouteView } from "./types";

/** Definitions the explorer shows for a route's itineraries. */
export const ROUTE_DEFINITIONS = [
  "connection_feasibility",
  "paired_days",
  "insufficient_data",
  "layover",
  "travel_time",
  "tight_layover",
  "flight_times",
  "faster_alternative",
  "connecting_option",
  "buffer",
  "failure_types",
  "monthly_rate",
  "connect_share",
  "schedule_change",
  "sold_passengers",
] as const;

export function buildRouteView(
  index: ShowcaseIndex,
  route: RouteFile,
  routeId: string,
): Result<RouteView> {
  const file = `routes/${routeId}.json`;
  const invalid = (detail: string, where = file): Result<RouteView> => ({
    ok: false,
    error: { kind: "invalid", file: where, detail },
  });
  if (route.route_id !== routeId) return invalid(`file is for ${route.route_id}`);
  for (const itinerary of route.itineraries) {
    const problem = itineraryProblem(index, itinerary);
    if (problem) return invalid(problem);
  }
  const ids = new Set(route.itineraries.map((i) => i.itinerary_id));
  for (const comparison of route.comparisons) {
    const problem = comparisonProblem(comparison);
    if (problem) return invalid(problem);
    if (!ids.has(comparison.itinerary_a) || !ids.has(comparison.itinerary_b)) {
      return invalid(`comparison ${comparison.comparison_id} lacks an itinerary`);
    }
  }
  const airport = (code: string): AirportInfo | undefined =>
    index.airports.find((a) => a.code === code);
  const [originCode = "", destCode = ""] = routeId.split("-");
  const origin = airport(originCode);
  const dest = airport(destCode);
  const hubs = [...new Set(route.itineraries.map((i) => i.hub))];
  const missingAirports = [originCode, destCode, ...hubs].filter((c) => !airport(c));
  if (!origin || !dest || missingAirports.length > 0) {
    return invalid(`no airport ${missingAirports.join(", ")}`, "index.json");
  }
  const missing = missingDefinitions(index, ROUTE_DEFINITIONS);
  if (missing.length > 0) return invalid(`no definition ${missing.join(", ")}`, "index.json");
  return {
    ok: true,
    value: { route, origin, dest, itineraries: byDeparture(route.itineraries) },
  };
}
