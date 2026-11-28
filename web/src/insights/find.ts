// "Find this itinerary" (FR-009): a Google Flights text search, no date, no fares.
import type { FindParams } from "@contract";

export function findUrl(find: FindParams, airlineNames: readonly string[]): string {
  const query = `Flights from ${find.origin} to ${find.dest} on ${airlineNames.join(" and ")}`;
  return `https://www.google.com/travel/flights?q=${encodeURIComponent(query)}`;
}
