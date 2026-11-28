// The selection lives in the address (ADR-0010): ?route=<route_id>&itinerary=<itinerary_id>.
// Pure functions; the hook in useSelection.ts applies them to the browser's history.

export interface Selection {
  routeId: string;
  itineraryId: string | null;
}

export interface Parsed {
  selection: Selection;
  /** Shown when a linked example was not found and the view fell back. */
  note: string | null;
}

interface IndexLike {
  routes: readonly { route_id: string }[];
  landing: { route_id: string };
}

export const NOT_FOUND = "The linked example was not found, so the default example is shown.";

export function parseSelection(search: string, index: IndexLike): Parsed {
  const params = new URLSearchParams(search);
  const route = params.get("route");
  const itinerary = params.get("itinerary");
  const fallback: Selection = { routeId: index.landing.route_id, itineraryId: null };
  if (route === null) {
    return { selection: fallback, note: itinerary === null ? null : NOT_FOUND };
  }
  if (!index.routes.some((r) => r.route_id === route)) {
    return { selection: fallback, note: NOT_FOUND };
  }
  return {
    selection: { routeId: route, itineraryId: itinerary === "" ? null : itinerary },
    note: null,
  };
}

/**
 * Checks the itinerary once the route's itineraries are known. An itinerary not on the route
 * opens the default view, like an unknown route (FR-010).
 */
export function resolveItinerary(
  selection: Selection,
  itineraryIds: readonly string[],
  landingRouteId: string,
): Parsed {
  if (selection.itineraryId === null || itineraryIds.includes(selection.itineraryId)) {
    return { selection, note: null };
  }
  return { selection: { routeId: landingRouteId, itineraryId: null }, note: NOT_FOUND };
}

/** The query string for a selection; the default view has none. */
export function serializeSelection(selection: Selection, landingRouteId: string): string {
  if (selection.routeId === landingRouteId && selection.itineraryId === null) return "";
  const params = new URLSearchParams({ route: selection.routeId });
  if (selection.itineraryId !== null) params.set("itinerary", selection.itineraryId);
  return `?${params.toString().replaceAll("%2C", ",")}`;
}
