import type { ShowcaseIndex } from "@contract";
import { useCallback, useEffect, useRef } from "react";
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
import { MapPanel } from "./MapPanel";
import { airportLabel, RoutePicker } from "./RoutePicker";
import { Timeline } from "./Timeline";

function LandingSection() {
  const landing = useLandingView();
  if (landing.state === "loading") return <Skeleton />;
  if (landing.state === "error") return <LoadError />;
  return <LandingComparison view={landing.view} />;
}

/** One route in three linked views, with the selection in the address (US1, US2). */
export function Explorer({ index }: { index: ShowcaseIndex }) {
  const { selection, note, choose, correct } = useSelection(index);
  const route = useRouteView(selection.routeId);
  const detailRef = useRef<HTMLDivElement>(null);
  // Arrow keys in a native select change the route once per keypress; consecutive route
  // changes replace one history entry instead of adding one each.
  const lastWasRoute = useRef(false);

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
      lastWasRoute.current = false;
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
          choose({ routeId, itineraryId: null }, lastWasRoute.current ? "replace" : "push");
          lastWasRoute.current = true;
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
