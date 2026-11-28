// Ordering and timeline layout (research R4). Lists are ordered by departure, never by rate.

interface Scheduled {
  itinerary_id: string;
  schedule: {
    dep_local_min: number;
    inbound_min: number;
    layover_min: number;
    travel_min: number;
  };
}

/** Earliest scheduled departure first; ties by id. Returns a new array. */
export function byDeparture<T extends Scheduled>(itineraries: readonly T[]): T[] {
  return [...itineraries].sort(
    (a, b) =>
      a.schedule.dep_local_min - b.schedule.dep_local_min ||
      a.itinerary_id.localeCompare(b.itinerary_id),
  );
}

export interface TimelineRow {
  id: string;
  /** Minutes after the route's earliest departure. */
  offset: number;
  inbound: number;
  layover: number;
  /** The rest of the published travel time, so the bar's length equals it. */
  outbound: number;
}

/**
 * One row per itinerary, in departure order, on an axis of minutes after the earliest
 * departure (origin local clock; every itinerary on a route leaves from the same airport).
 */
export function timelineRows(itineraries: readonly Scheduled[]): {
  rows: TimelineRow[];
  start: number;
  extent: number;
} {
  const ordered = byDeparture(itineraries);
  const first = ordered[0];
  if (!first) return { rows: [], start: 0, extent: 0 };
  const start = first.schedule.dep_local_min;
  const rows = ordered.map((it) => {
    const s = it.schedule;
    const inbound = Math.min(s.inbound_min, s.travel_min);
    const layover = Math.min(s.layover_min, s.travel_min - inbound);
    return {
      id: it.itinerary_id,
      offset: s.dep_local_min - start,
      inbound,
      layover,
      outbound: s.travel_min - inbound - layover,
    };
  });
  const extent = Math.max(
    ...ordered.map((it) => it.schedule.dep_local_min - start + it.schedule.travel_min),
  );
  return { rows, start, extent };
}
