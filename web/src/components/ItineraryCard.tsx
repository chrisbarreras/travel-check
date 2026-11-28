import type { ShowcaseItinerary } from "@contract";
import {
  airlineName,
  arrivalDayOffset,
  duration,
  excludedText,
  flightNumbers,
  localTime,
  rateText,
} from "../format";

/** "Delta via ATL", or "Delta and Alaska via ATL" when the flights are on two airlines. */
export function itineraryName(itinerary: ShowcaseItinerary): string {
  const inbound = airlineName(itinerary.airline);
  const airlines =
    itinerary.airline_out === itinerary.airline
      ? inbound
      : `${inbound} and ${airlineName(itinerary.airline_out)}`;
  return `${airlines} via ${itinerary.hub}`;
}

function Time({ minutes, dayOffset = 0 }: { minutes: number; dayOffset?: number }) {
  const { text } = localTime(minutes);
  return (
    <>
      {text}
      {dayOffset !== 0 ? (
        <span className="day-offset">
          {" "}
          {dayOffset > 0 ? "+" : "−"}
          {Math.abs(dayOffset) === 1 ? "1 day" : `${String(Math.abs(dayOffset))} days`}
        </span>
      ) : null}
    </>
  );
}

/** One itinerary: flights, schedule and how often it worked (data-model.md, Fields shown). */
export function ItineraryCard({
  itinerary,
  headingId,
  period,
  badge,
}: {
  itinerary: ShowcaseItinerary;
  headingId: string;
  period: string;
  badge?: string | undefined;
}) {
  const rate = rateText(itinerary.result, period);
  const excluded = excludedText(itinerary.excluded_days);
  const flights = flightNumbers(itinerary.find.legs);
  const [inbound, outbound] = flights.numbers;
  return (
    <article className={badge ? "card card--higher" : "card"} aria-labelledby={headingId}>
      {badge ? <p className="badge">{badge}</p> : null}
      <h3 id={headingId}>{itineraryName(itinerary)}</h3>
      <p className="rate">
        {rate.kind === "ok" ? (
          <>
            <span className="rate-value" aria-hidden="true">
              {rate.percent}%
            </span>
            <span className="rate-text">{rate.text}</span>
          </>
        ) : (
          <span className="rate-text insufficient">{rate.text}</span>
        )}
      </p>
      <dl className="facts">
        <div>
          <dt>Flights</dt>
          <dd>
            {flights.varies ? "Most often " : null}
            {inbound}
            {outbound ? <>, then {outbound}</> : null}
            {flights.varies ? (
              <span className="flights-note">; flown under other numbers on some days</span>
            ) : null}
          </dd>
        </div>
        <div>
          <dt>Departs</dt>
          <dd>
            <Time minutes={itinerary.schedule.dep_local_min} /> local time
          </dd>
        </div>
        <div>
          <dt>Arrives</dt>
          <dd>
            <Time
              minutes={itinerary.schedule.arr_local_min}
              dayOffset={arrivalDayOffset(itinerary.schedule)}
            />{" "}
            local time
          </dd>
        </div>
        <div>
          <dt>Layover</dt>
          <dd>
            {duration(itinerary.schedule.layover_min)} at {itinerary.hub}
          </dd>
        </div>
        <div>
          <dt>Travel time</dt>
          <dd>{duration(itinerary.schedule.travel_min)}</dd>
        </div>
      </dl>
      {excluded.length > 0 ? (
        <div className="excluded">
          <p>Not counted:</p>
          <ul>
            {excluded.map((line) => (
              <li key={line}>{line}</li>
            ))}
          </ul>
        </div>
      ) : null}
    </article>
  );
}
