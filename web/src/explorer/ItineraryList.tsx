import type { Definition as DefinitionRecord, ShowcaseItinerary } from "@contract";
import { Definition } from "../components/Definition";
import { itineraryName } from "../components/ItineraryCard";
import { arrivalDayOffset, duration, flightNumbers, localTime, rateText } from "../format";

/** "12:38 pm to 7:13 pm, local times", with the arrival day when it differs. */
export function timesText(itinerary: ShowcaseItinerary): string {
  const dep = localTime(itinerary.schedule.dep_local_min).text;
  const arr = localTime(itinerary.schedule.arr_local_min).text;
  const offset = arrivalDayOffset(itinerary.schedule);
  const day = offset === 0 ? "" : ` ${offset > 0 ? "+" : "−"}${String(Math.abs(offset))} day`;
  return `${dep} to ${arr}${day}, local times`;
}

/** "Most often DL3080, then DL524; other numbers on some days", as on the detail card. */
export function flightsText(itinerary: ShowcaseItinerary): string {
  const flights = flightNumbers(itinerary.find.legs);
  const numbers = flights.numbers.join(", then ");
  return flights.varies ? `Most often ${numbers}; other numbers on some days` : numbers;
}

/** The route's itineraries in departure order; each card selects its itinerary (FR-005). */
export function ItineraryList({
  itineraries,
  selectedId,
  period,
  definition,
  onSelect,
}: {
  itineraries: readonly ShowcaseItinerary[];
  selectedId: string | null;
  period: string;
  /** Looks up a published definition by key. */
  definition: (key: string) => DefinitionRecord | undefined;
  onSelect: (id: string) => void;
}) {
  return (
    <section className="itinerary-list" aria-labelledby="list-heading">
      <h3 id="list-heading">Itineraries, by departure time</h3>
      <div className="list-definitions">
        <Definition
          summary="What “worked” means"
          definition={definition("connection_feasibility")}
        />
        <Definition summary="Which days count" definition={definition("paired_days")} />
        <Definition summary="Layover" definition={definition("layover")} />
        <Definition summary="Tight layover" definition={definition("tight_layover")} />
      </div>
      <ul>
        {itineraries.map((it) => {
          const selected = it.itinerary_id === selectedId;
          const rate = rateText(it.result, period);
          return (
            <li key={it.itinerary_id}>
              <button
                type="button"
                className={selected ? "list-card selected" : "list-card"}
                aria-pressed={selected}
                data-itinerary={it.itinerary_id}
                onClick={() => {
                  onSelect(it.itinerary_id);
                }}
              >
                <span className="list-card-title">
                  {itineraryName(it)}
                  {selected ? <span className="selected-label"> · Selected</span> : null}
                </span>
                <span>{flightsText(it)}</span>
                <span>{timesText(it)}</span>
                <span>
                  Layover {duration(it.schedule.layover_min)} at {it.hub}
                </span>
                <span
                  className={rate.kind === "ok" ? "list-card-rate" : "list-card-rate insufficient"}
                >
                  {rate.text}
                </span>
                {it.tight_layover ? <span className="badge warn">Tight layover</span> : null}
              </button>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
