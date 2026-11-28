import type { AirportInfo, ShowcaseItinerary } from "@contract";
import { Component, lazy, Suspense, useState, type ReactNode } from "react";
import { airportLabel } from "./RoutePicker";

const MapView = lazy(() => import("../map/MapView"));

/** If the map chunk or WebGL fails, say so; the list and timeline keep working (FR-012). */
class MapBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  override state = { failed: false };

  static getDerivedStateFromError(): { failed: boolean } {
    return { failed: true };
  }

  override componentDidCatch(error: unknown): void {
    console.error("Travel Check: the map could not be shown", error);
  }

  override render(): ReactNode {
    return this.state.failed ? (
      <p className="map-fallback">
        The map could not be shown. The list and timeline have every itinerary.
      </p>
    ) : (
      this.props.children
    );
  }
}

function wideScreen(): boolean {
  return typeof window.matchMedia !== "function" || window.matchMedia("(min-width: 768px)").matches;
}

/** The map with its text equivalent and, on phones, a show/hide button (FR-013). */
export function MapPanel({
  airports,
  origin,
  dest,
  itineraries,
  selectedId,
  onSelect,
}: {
  airports: readonly AirportInfo[];
  origin: string;
  dest: string;
  itineraries: readonly ShowcaseItinerary[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}) {
  const [shown, setShown] = useState(wideScreen);
  const hubs = [...new Set(itineraries.map((i) => i.hub))].sort();
  const label = (code: string) => airportLabel(airports, code);
  return (
    <section className="map-panel" aria-labelledby="map-heading">
      <div className="map-header">
        <h3 id="map-heading">Map</h3>
        <button
          type="button"
          className="map-toggle"
          aria-expanded={shown}
          aria-controls="map-area"
          onClick={() => {
            setShown((s) => !s);
          }}
        >
          {shown ? "Hide map" : "Show map"}
        </button>
      </div>
      <p className="visually-hidden" id="map-description">
        Map of {itineraries.length} itineraries from {label(origin)} to {label(dest)}, through{" "}
        {hubs.map(label).join(", ")}. The selected itinerary is drawn as a thick solid line, the
        others as thin dashed lines. The list and timeline give the same itineraries as text.
      </p>
      <div id="map-area" className="map-area" hidden={!shown} aria-describedby="map-description">
        {shown ? (
          <MapBoundary>
            <Suspense fallback={<p className="map-fallback">Loading the map…</p>}>
              <MapView
                airports={airports}
                origin={origin}
                dest={dest}
                itineraries={itineraries}
                selectedId={selectedId}
                onSelect={onSelect}
              />
            </Suspense>
          </MapBoundary>
        ) : null}
      </div>
    </section>
  );
}
