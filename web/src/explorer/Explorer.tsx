import type { ShowcaseIndex } from "@contract";
import { useCallback, useEffect, useRef, useState } from "react";
import { itineraryName } from "../components/ItineraryCard";
import { LandingComparison } from "../components/LandingComparison";
import { LoadError } from "../components/LoadError";
import { Skeleton } from "../components/Skeleton";
import { useLandingView, useRouteView } from "../data";
import { periodText } from "../format";
import { resolveItinerary } from "../selection/url";
import { useSelection } from "../selection/useSelection";
import { DetailPanel } from "./DetailPanel";
import { ItineraryList } from "./ItineraryList";
import { MapPanel, wideScreen } from "./MapPanel";
import { airportLabel, RoutePicker } from "./RoutePicker";
import { Timeline } from "./Timeline";

function LandingSection() {
  const landing = useLandingView();
  if (landing.state === "loading") return <Skeleton />;
  if (landing.state === "error") return <LoadError />;
  return <LandingComparison view={landing.view} />;
}

/** Route changes closer together than this are one choice (keyboard in the native select). */
const ROUTE_KEYS_MS = 1000;

/** One route in three linked views, with the selection in the address (US1, US2). */
export function Explorer({ index }: { index: ShowcaseIndex }) {
  const { selection, note, choose, correct } = useSelection(index);
  const route = useRouteView(selection.routeId);
  const detailRef = useRef<HTMLDivElement>(null);
  // Arrow keys in a native select change the route once per keypress. Changes less than a
  // second apart are one choice, sharing one history entry; any later choice adds its own.
  const lastRouteChange = useRef(Number.NEGATIVE_INFINITY);
  // Back and Forward end a run of route-picker changes: the next choice adds an entry.
  useEffect(() => {
    const onPop = () => {
      lastRouteChange.current = Number.NEGATIVE_INFINITY;
    };
    window.addEventListener("popstate", onPop);
    return () => {
      window.removeEventListener("popstate", onPop);
    };
  }, []);

  // Kept here, so the map stays shown or hidden across route changes (FR-013).
  const [mapShown, setMapShown] = useState(wideScreen);

  // An itinerary that is not on the route falls back, with a note (FR-010).
  useEffect(() => {
    if (route.state !== "ready") return;
    const resolved = resolveItinerary(
      selection,
      route.view.itineraries.map((i) => i.itinerary_id),
      index.landing.route_id,
    );
    if (resolved.note !== null) correct(resolved.selection, resolved.note);
  }, [route, selection, correct, index.landing.route_id]);

  const select = useCallback(
    (itineraryId: string) => {
      lastRouteChange.current = Number.NEGATIVE_INFINITY;
      choose({ routeId: selection.routeId, itineraryId });
      detailRef.current?.scrollIntoView({ block: "start" });
    },
    [choose, selection.routeId],
  );

  const label = (code: string) => airportLabel(index.airports, code);
  const [originCode = "", destCode = ""] = selection.routeId.split("-");
  const selected =
    route.state === "ready" && selection.itineraryId !== null
      ? route.view.itineraries.find((i) => i.itinerary_id === selection.itineraryId)
      : undefined;
  const isLanding = selection.routeId === index.landing.route_id;

  return (
    <section className="explorer" aria-labelledby="route-heading">
      <RoutePicker
        index={index}
        routeId={selection.routeId}
        onChoose={(routeId) => {
          const now = Date.now();
          const rapid = now - lastRouteChange.current < ROUTE_KEYS_MS;
          choose({ routeId, itineraryId: null }, rapid ? "replace" : "push");
          lastRouteChange.current = now;
        }}
      />
      {note !== null ? (
        <p className="note" role="status">
          {note}
        </p>
      ) : null}
      <p className="visually-hidden" aria-live="polite">
        {selected ? `Selected: ${itineraryName(selected)}` : ""}
      </p>
      <h2 id="route-heading">
        {label(originCode)} to {label(destCode)}
      </h2>
      {route.state === "loading" ? <Skeleton /> : null}
      {route.state === "error" ? <LoadError /> : null}
      {route.state === "ready" ? (
        <>
          <p className="muted">
            {route.view.itineraries.length} one-stop itineraries,{" "}
            {periodText(route.view.route.period)}. Select one in the list, the timeline or the map.
          </p>
          <div className="detail-slot" ref={detailRef}>
            {selected ? (
              <DetailPanel
                itinerary={selected}
                index={index}
                route={route.view.route}
                onSelect={select}
                period={periodText(route.view.route.period)}
              />
            ) : isLanding ? (
              <LandingSection />
            ) : (
              <p className="prompt">Select an itinerary to see how often it worked.</p>
            )}
          </div>
          <div className="explorer-grid">
            <ItineraryList
              itineraries={route.view.itineraries}
              selectedId={selection.itineraryId}
              period={periodText(route.view.route.period)}
              definition={(key) => index.definitions.find((d) => d.key === key)}
              onSelect={select}
            />
            <Timeline
              itineraries={route.view.itineraries}
              originCode={originCode}
              destCode={destCode}
              definition={index.definitions.find((d) => d.key === "flight_times")}
              selectedId={selection.itineraryId}
              onSelect={select}
            />
            <MapPanel
              shown={mapShown}
              onToggle={() => {
                setMapShown((s) => !s);
              }}
              airports={index.airports}
              origin={originCode}
              dest={destCode}
              itineraries={route.view.itineraries}
              selectedId={selection.itineraryId}
              onSelect={select}
            />
          </div>
        </>
      ) : null}
    </section>
  );
}
