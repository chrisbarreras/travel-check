import type { ShowcaseItinerary } from "@contract";
import { itineraryName } from "../components/ItineraryCard";
import { duration } from "../format";
import { timelineRows } from "../format/timeline";
import { timesText } from "./ItineraryList";

const HOUR = 60;

/**
 * Each itinerary's inbound flight, layover and outbound flight on one axis of hours after the
 * route's earliest departure (research R4). Each bar is a button with a full text label.
 */
export function Timeline({
  itineraries,
  originCode,
  selectedId,
  onSelect,
}: {
  itineraries: readonly ShowcaseItinerary[];
  originCode: string;
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
        Hours after the first departure, on {originCode} local time. Dark: flights; light: layover.
      </p>
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
          const label =
            `${itineraryName(it)}${selected ? " · Selected" : ""}: ${timesText(it)}. ` +
            `Flight ${duration(row.inbound)}, layover ${duration(row.layover)} at ${it.hub}, ` +
            `flight ${duration(row.outbound)}.`;
          return (
            <li key={row.id}>
              <button
                type="button"
                className={selected ? "timeline-row selected" : "timeline-row"}
                aria-pressed={selected}
                aria-label={label}
                data-itinerary={row.id}
                onClick={() => {
                  onSelect(row.id);
                }}
              >
                <span className="timeline-name" aria-hidden="true">
                  {itineraryName(it)}
                  {selected ? " · Selected" : ""}
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
