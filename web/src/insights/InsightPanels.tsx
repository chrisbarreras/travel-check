// Traveler-insight panels for the selected itinerary (spec US3, US4). Every figure comes from
// the published data, with its definition; a panel with nothing to suggest says so.
import type { RouteFile, ShowcaseIndex, ShowcaseItinerary } from "@contract";
import type { ReactNode } from "react";
import { Definition } from "../components/Definition";
import { itineraryName } from "../components/ItineraryCard";
import { airlineName, duration, intervalText, localTime, percentOf, rateText } from "../format";
import { findUrl } from "./find";
import { FailureBar, MonthChart } from "./Visuals";

/** "Delta via ATL" from an id such as "LIT-ATL-LGA:DL1238+DL1700". */
export function nameFromId(itineraryId: string): string {
  const [route = "", flights = ""] = itineraryId.split(":");
  const hub = route.split("-")[1] ?? "";
  const codes = [...new Set(flights.split("+").map((f) => f.replace(/\d+$/, "")))];
  return `${codes.map(airlineName).join(" and ")} via ${hub}`;
}

function Panel({
  title,
  children,
  definition,
  summary,
}: {
  title: string;
  children: ReactNode;
  definition?: ReturnType<ShowcaseIndex["definitions"]["find"]>;
  summary?: string;
}) {
  const id = `panel-${title.toLowerCase().replace(/[^a-z]+/g, "-")}`;
  return (
    <section className="panel" aria-labelledby={id}>
      <h4 id={id}>{title}</h4>
      {children}
      {definition && summary ? <Definition summary={summary} definition={definition} /> : null}
    </section>
  );
}

export function InsightPanels({
  itinerary,
  route,
  index,
  period,
  onSelect,
}: {
  itinerary: ShowcaseItinerary;
  route: RouteFile;
  index: ShowcaseIndex;
  period: string;
  onSelect: (id: string) => void;
}) {
  const def = (key: string) => index.definitions.find((d) => d.key === key);
  const byId = new Map(route.itineraries.map((i) => [i.itinerary_id, i]));
  const better = itinerary.connecting_options.filter((o) => o.better);
  const others = itinerary.connecting_options.filter((o) => !o.better);
  const warnings = itinerary.schedule_warnings;
  const airlines = [...new Set([itinerary.airline, itinerary.airline_out])].map(airlineName);
  return (
    <div className="panels">
      <Panel
        title="Faster, just as reliable"
        definition={def("faster_alternative")}
        summary="What “just as reliable” means"
      >
        {itinerary.faster_alternatives.length === 0 ? (
          <p>No faster itinerary on this route was as reliable.</p>
        ) : (
          <ul className="suggestions">
            {itinerary.faster_alternatives.map((a) => {
              const other = byId.get(a.itinerary_id);
              return (
                <li key={a.itinerary_id} data-alternative={a.itinerary_id}>
                  {other ? (
                    <button
                      type="button"
                      className="link-button"
                      onClick={() => {
                        onSelect(a.itinerary_id);
                      }}
                    >
                      {itineraryName(other)}
                    </button>
                  ) : (
                    // Not among this route's showcase itineraries: described, not selectable.
                    <span>{nameFromId(a.itinerary_id)} (not shown on this route)</span>
                  )}
                  : {a.minutes_saved} min shorter; {rateText(a.rate_other, period).text}, against{" "}
                  {rateText(a.rate_this, period).text} for this one. The faster one minus this one:{" "}
                  {intervalText(a.ci_low, a.ci_high)}, over {a.shared_days} days both flew.
                </li>
              );
            })}
          </ul>
        )}
      </Panel>

      <Panel
        title="Better connecting flight"
        definition={def("connecting_option")}
        summary="What a connecting option is"
      >
        {better.length === 0 ? (
          <p>
            No other outbound flight from {itinerary.hub} worked more often with this inbound
            flight.
          </p>
        ) : (
          <ul className="suggestions">
            {better.map((o) => (
              <li key={o.itinerary_id}>
                Leaving {itinerary.hub} at {localTime(o.outbound_dep_local_min).text} local time:{" "}
                {rateText(o.rate, period).text}
                {o.ci_low !== null && o.ci_high !== null
                  ? ` (${intervalText(o.ci_low, o.ci_high)} against this one)`
                  : ""}
                .
              </li>
            ))}
          </ul>
        )}
        {others.length > 0 ? (
          <p className="muted">
            Other outbound flights from {itinerary.hub}:{" "}
            {others
              .map(
                (o) =>
                  `${localTime(o.outbound_dep_local_min).text} (${rateText(o.rate, period).text})`,
              )
              .join("; ")}
            .
          </p>
        ) : null}
      </Panel>

      <Panel title="Buffer you needed" definition={def("buffer")} summary="How the buffer is found">
        {itinerary.buffer.needed_layover_min === null ||
        itinerary.buffer.scheduled_at_least_share === null ? (
          <p>
            No layover would have been enough on {Math.round(itinerary.buffer.share * 100)}% of the{" "}
            {itinerary.buffer.operated_days} operated days, or there are too few days to say.
          </p>
        ) : (
          <p>
            To have connected on {Math.round(itinerary.buffer.share * 100)}% of the{" "}
            {itinerary.buffer.operated_days} operated days in {period}, at the published{" "}
            {itinerary.min_connection_min}-minute minimum connection time, the scheduled layover
            needed to be at least {duration(itinerary.buffer.needed_layover_min)}. This
            itinerary&apos;s median is {duration(itinerary.buffer.actual_layover_min)}; it was
            scheduled at least {duration(itinerary.buffer.needed_layover_min)} on{" "}
            {Math.round(itinerary.buffer.scheduled_at_least_share * 100)}% of those days.
          </p>
        )}
      </Panel>

      <Panel
        title="Why it didn't work"
        definition={def("failure_types")}
        summary="What the failure types are"
      >
        <p className="muted">
          At the published {itinerary.min_connection_min}-minute minimum connection time, of{" "}
          {itinerary.result.paired_days} days, {period}. The slider above doesn&apos;t change these
          counts.
        </p>
        <FailureBar failures={itinerary.failures} />
      </Panel>

      <Panel title="By month" definition={def("monthly_rate")} summary="What the monthly rate is">
        <p className="muted">
          At the published {itinerary.min_connection_min}-minute minimum connection time, {period}.
        </p>
        <MonthChart monthly={itinerary.monthly} notes={route.disruption_notes} />
        <Definition summary="What the notes are" definition={def("disruption_note")} />
      </Panel>

      <Panel
        title="About this itinerary"
        definition={def("connect_share")}
        summary="How often it connects"
      >
        <p>
          The two flights were scheduled to connect on {warnings.connecting_days} of{" "}
          {warnings.eligible_days} days (
          {percentOf(warnings.connecting_days, Math.max(warnings.eligible_days, 1))}%).
        </p>
        {warnings.changes.length === 0 ? (
          <p>No lasting schedule changes in the period.</p>
        ) : (
          <>
            <p>Schedule changes in the period:</p>
            <ul>
              {warnings.changes.map((c) => (
                <li key={`${c.date}-${c.leg}`}>
                  {c.date}: the {c.leg} flight moved from {localTime(c.from_local_min).text} to{" "}
                  {localTime(c.to_local_min).text} local time.
                </li>
              ))}
            </ul>
          </>
        )}
        <p>
          {itinerary.sold.passengers} sampled passengers flew this routing in the period, shared by{" "}
          {itinerary.sold.routing_itineraries} itineraries on it.
        </p>
        <Definition summary="What the schedule changes are" definition={def("schedule_change")} />
        <Definition summary="What the passenger count is" definition={def("sold_passengers")} />
      </Panel>

      <p className="find">
        <a
          className="button-link"
          href={findUrl(itinerary.find, airlines)}
          target="_blank"
          rel="noopener noreferrer"
        >
          Find this itinerary on Google Flights
        </a>{" "}
        <span className="muted">
          Opens a search in a new tab. Prices come from that site; this app neither sees nor stores
          them.
        </span>
      </p>
    </div>
  );
}
