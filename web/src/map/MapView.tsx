// The route map (FR-006): loaded as its own chunk after the first view (FR-012).
import "maplibre-gl/dist/maplibre-gl.css";
import {
  AttributionControl,
  Layer,
  Map,
  Marker,
  Source,
  type MapLayerMouseEvent,
} from "@vis.gl/react-maplibre";
import type { Map as MapLibreMap } from "maplibre-gl";
import { useMemo } from "react";
import { airportPoints, bounds, routePaths, type AirportLike } from "./geometry";

export interface MapViewProps {
  airports: readonly AirportLike[];
  origin: string;
  dest: string;
  itineraries: readonly { itinerary_id: string; hub: string }[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}

const STYLE_URL: string =
  (import.meta.env.VITE_BASEMAP_STYLE as string | undefined) ??
  `${import.meta.env.BASE_URL}basemap-style.json`;

// Exactly the tile source's own attribution, so MapLibre shows it once when the tiles load,
// and it is still shown when they don't (docs/design.md, Map).
const ATTRIBUTION =
  '<a href="https://openfreemap.org" target="_blank">OpenFreeMap</a> <a href="https://www.openmaptiles.org/" target="_blank">&copy; OpenMapTiles</a> Data from <a href="https://www.openstreetmap.org/copyright" target="_blank">OpenStreetMap</a>';

declare global {
  interface Window {
    /** Set by the end-to-end tests only, to read rendered features (research R6). */
    __travelCheckTest?: boolean;
    __travelCheckMap?: MapLibreMap;
  }
}

export default function MapView({
  airports,
  origin,
  dest,
  itineraries,
  selectedId,
  onSelect,
}: MapViewProps) {
  const paths = useMemo(
    () => routePaths(airports, origin, dest, itineraries),
    [airports, origin, dest, itineraries],
  );
  const points = useMemo(
    () => airportPoints(airports, origin, dest, itineraries),
    [airports, origin, dest, itineraries],
  );
  const box = useMemo(() => bounds(points), [points]);
  const selected = selectedId ?? "";

  return (
    <Map
      key={`${origin}-${dest}`}
      initialViewState={{ bounds: box, fitBoundsOptions: { padding: 32 } }}
      mapStyle={STYLE_URL}
      attributionControl={false}
      dragRotate={false}
      touchPitch={false}
      interactiveLayerIds={["paths-hit"]}
      cursor="pointer"
      onClick={(e: MapLayerMouseEvent) => {
        // Itineraries through one hub share a path. A click on a path the current selection
        // shares keeps it; otherwise the earliest id under the pointer is chosen, so the result
        // never depends on MapLibre's hit order.
        const ids = (e.features ?? [])
          .map((f) => f.properties.itinerary_id as unknown)
          .filter((id): id is string => typeof id === "string");
        if (ids.length === 0 || (selectedId !== null && ids.includes(selectedId))) return;
        const first = [...ids].sort()[0];
        if (first !== undefined) onSelect(first);
      }}
      onLoad={(e) => {
        // Fit again once the map has measured its panel, so the view does not depend on
        // when the panel finished laying out.
        e.target.resize();
        e.target.fitBounds(box, { padding: 32, animate: false });
        if (window.__travelCheckTest) window.__travelCheckMap = e.target;
      }}
      style={{ width: "100%", height: "100%" }}
    >
      <AttributionControl compact={false} customAttribution={ATTRIBUTION} />
      <Source id="paths" type="geojson" data={paths}>
        <Layer
          id="paths-other"
          type="line"
          filter={["!=", ["get", "itinerary_id"], selected]}
          layout={{ "line-cap": "round", "line-join": "round" }}
          paint={{ "line-color": "#1c56c2", "line-width": 1.5, "line-dasharray": [2, 2] }}
        />
        <Layer
          id="paths-selected"
          type="line"
          filter={["==", ["get", "itinerary_id"], selected]}
          layout={{ "line-cap": "round", "line-join": "round" }}
          paint={{ "line-color": "#123e8f", "line-width": 4.5 }}
        />
        <Layer
          id="paths-hit"
          type="line"
          paint={{ "line-color": "#000000", "line-opacity": 0, "line-width": 14 }}
        />
      </Source>
      {points.map((p) => (
        <Marker
          key={p.code}
          longitude={p.lon}
          latitude={p.lat}
          anchor="center"
          ref={(marker) => {
            // Markers are decoration: the map's text description and the list carry the
            // information. MapLibre labels each one "Map marker", which screen readers would
            // read instead of the code shown.
            const el = marker?.getElement();
            el?.removeAttribute("aria-label");
            el?.removeAttribute("tabindex");
            el?.setAttribute("aria-hidden", "true");
          }}
        >
          <span className={`map-airport ${p.role}`} title={`${p.name}, ${p.city}`}>
            <span className="map-dot" />
            <span className="map-label">{p.code}</span>
          </span>
        </Marker>
      ))}
    </Map>
  );
}
