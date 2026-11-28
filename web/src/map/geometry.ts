// Pure map geometry (constitution II: map logic in pure, unit-tested functions; research R2).
import greatCircle from "@turf/great-circle";

export interface AirportLike {
  code: string;
  name: string;
  city: string;
  lat: number;
  lon: number;
}

interface ItineraryLike {
  itinerary_id: string;
  hub: string;
}

export type Position = [number, number];

export interface PathFeature {
  type: "Feature";
  properties: { itinerary_id: string; hub: string };
  geometry: { type: "LineString"; coordinates: Position[] };
}

export interface PathCollection {
  type: "FeatureCollection";
  features: PathFeature[];
}

function lookup(airports: readonly AirportLike[], code: string): AirportLike {
  const found = airports.find((a) => a.code === code);
  if (!found) throw new Error(`no airport ${code} in the index`);
  return found;
}

/** A great-circle arc between two airports, as positions. */
function arc(from: AirportLike, to: AirportLike): Position[] {
  const line = greatCircle([from.lon, from.lat], [to.lon, to.lat], { npoints: 32 });
  const g = line.geometry;
  const parts: Position[][] =
    g.type === "LineString" ? [g.coordinates as Position[]] : (g.coordinates as Position[][]);
  return parts.flat();
}

/** One curved line per itinerary: origin to its hub, then hub to destination. */
export function routePaths(
  airports: readonly AirportLike[],
  origin: string,
  dest: string,
  itineraries: readonly ItineraryLike[],
): PathCollection {
  const from = lookup(airports, origin);
  const to = lookup(airports, dest);
  return {
    type: "FeatureCollection",
    features: itineraries.map((it) => {
      const hub = lookup(airports, it.hub);
      return {
        type: "Feature",
        properties: { itinerary_id: it.itinerary_id, hub: it.hub },
        geometry: {
          type: "LineString",
          coordinates: [...arc(from, hub), ...arc(hub, to).slice(1)],
        },
      };
    }),
  };
}

export interface AirportPoint extends AirportLike {
  role: "origin" | "destination" | "hub";
}

/** The route's airports: origin, destination, then each hub once (in itinerary order). */
export function airportPoints(
  airports: readonly AirportLike[],
  origin: string,
  dest: string,
  itineraries: readonly ItineraryLike[],
): AirportPoint[] {
  const hubs = [...new Set(itineraries.map((i) => i.hub))].sort();
  return [
    { ...lookup(airports, origin), role: "origin" },
    { ...lookup(airports, dest), role: "destination" },
    ...hubs.map((code) => ({ ...lookup(airports, code), role: "hub" as const })),
  ];
}

/** [[west, south], [east, north]] around the points, with a margin of 10% (at least 1°). */
export function bounds(points: readonly { lat: number; lon: number }[]): [Position, Position] {
  const lons = points.map((p) => p.lon);
  const lats = points.map((p) => p.lat);
  const padLon = Math.max((Math.max(...lons) - Math.min(...lons)) * 0.1, 1);
  const padLat = Math.max((Math.max(...lats) - Math.min(...lats)) * 0.1, 1);
  return [
    [Math.min(...lons) - padLon, Math.min(...lats) - padLat],
    [Math.max(...lons) + padLon, Math.max(...lats) + padLat],
  ];
}
