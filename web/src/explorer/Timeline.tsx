import type { Definition as DefinitionRecord, ShowcaseItinerary } from "@contract";
import { Definition } from "../components/Definition";
import { itineraryName } from "../components/ItineraryCard";
import { arrivalDayOffset, duration, localTime } from "../format";
import { timelineRows } from "../format/timeline";

/** The visible times on a bar: each in its own airport's local time (spec US1-4). */
export function barTimes(it: ShowcaseItinerary, originCode: string, destCode: string): string {
  const t = (m: number) => localTime(m).text;
  const s = it.schedule;
  const day = (offset: number) =>
    offset === 0 ? "" : ` ${offset > 0 ? "+" : "−"}${String(Math.abs(offset))} day`;
  // Days after the departure day, from clock times and the published durations only.
  const hubArrDay = arrivalDayOffset({
    dep_local_min: s.dep_local_min,
    arr_local_min: s.hub_arr_local_min,
    travel_min: s.inbound_min,
  });
  const hubDepDay = hubArrDay + (s.hub_arr_local_min + s.layover_min >= 1440 ? 1 : 0);
  return (
    `${t(s.dep_local_min)} ${originCode} → ` +
    `${t(s.hub_arr_local_min)}${day(hubArrDay)}–${t(s.hub_dep_local_min)}${day(hubDepDay)} ` +
    `${it.hub} → ${t(s.arr_local_min)}${day(arrivalDayOffset(s))} ${destCode}`
  );
}

const HOUR = 60;

/**
 * Each itinerary's inbound flight, layover and outbound flight on one axis of hours after the
 * route's earliest departure (research R4). Each bar is a button with a full text label.
 */
export function Timeline({
  itineraries,
  originCode,
  destCode,
  definition,
  selectedId,
  onSelect,
}: {
  itineraries: readonly ShowcaseItinerary[];
  originCode: string;
  destCode: string;
  definition: DefinitionRecord | undefined;
  selectedId: string | null;
  onSelect: (id: string) => void;
}) {
  const { rows, extent } = timelineRows(itineraries);
  const span = Math.max(Math.ceil(extent / HOUR), 1) * HOUR;
  // Every 2 hours, or every 4 on long spans, so labels never crowd on a phone.
  const step = span > 12 * HOUR ? 4 : 2;
  const ticks = Array.from({ length: span / HOUR + 1 }, (_, i) => i).filter((t) => t % step === 0);
  const pct = (minutes: number) => `${String((minutes / span) * 100)}%`;
  const byId = new Map(itineraries.map((it) => [it.itinerary_id, it]));
  return (
    <section className="timeline" aria-labelledby="timeline-heading">
      <h3 id="timeline-heading">Timeline</h3>
      <p className="muted">
        Bars: hours after the first departure, on {originCode} local time. Dark: flights; light:
        layover. Times: each airport&apos;s local time.
      </p>
      <Definition summary="How these times are found" definition={definition} />
      <div className="timeline-axis" aria-hidden="true">
        {ticks.map((t) => (
          <span key={t} style={{ left: pct(t * HOUR) }}>
            +{t} h
          </span>
        ))}
      </div>
      <ul>
        {rows.map((row) => {
          const it = byId.get(row.id);
          if (!it) return null;
          const selected = row.id === selectedId;
          const name = `${itineraryName(it)}${selected ? " · Selected" : ""}`;
          const times = barTimes(it, originCode, destCode);
          const durations =
            `. Flight ${duration(row.inbound)}, layover ${duration(row.layover)} at ${it.hub}, ` +
            `flight ${duration(row.outbound)}.`;
          return (
            <li key={row.id}>
              <button
                type="button"
                className={selected ? "timeline-row selected" : "timeline-row"}
                aria-pressed={selected}
                data-itinerary={row.id}
                onClick={() => {
                  onSelect(row.id);
                }}
              >
                <span className="timeline-name">{name}</span>
                <span className="timeline-times">
                  <span className="visually-hidden">. </span>
                  {times}
                  <span className="visually-hidden">{durations}</span>
                </span>
                <span className="timeline-track" aria-hidden="true">
                  <span
                    className="seg flight"
                    style={{ left: pct(row.offset), width: pct(row.inbound) }}
                  />
                  <span
                    className="seg layover"
                    style={{ left: pct(row.offset + row.inbound), width: pct(row.layover) }}
                  />
                  <span
                    className="seg flight"
                    style={{
                      left: pct(row.offset + row.inbound + row.layover),
                      width: pct(row.outbound),
                    }}
                  />
                </span>
              </button>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
