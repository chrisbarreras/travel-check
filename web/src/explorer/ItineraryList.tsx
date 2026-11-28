import type { ShowcaseItinerary } from "@contract";
import { itineraryName } from "../components/ItineraryCard";
import { arrivalDayOffset, localTime, rateText } from "../format";

/** "12:38 pm to 7:13 pm, local times", with the arrival day when it differs. */
export function timesText(itinerary: ShowcaseItinerary): string {
  const dep = localTime(itinerary.schedule.dep_local_min).text;
  const arr = localTime(itinerary.schedule.arr_local_min).text;
  const offset = arrivalDayOffset(itinerary.schedule);
  const day = offset === 0 ? "" : ` ${offset > 0 ? "+" : "−"}${String(Math.abs(offset))} day`;
  return `${dep} to ${arr}${day}, local times`;
}

/** The route's itineraries in departure order; each card selects its itinerary (FR-005). */
export function ItineraryList({
  itineraries,
  selectedId,
  period,
  onSelect,
}: {
  itineraries: readonly ShowcaseItinerary[];
  selectedId: string | null;
  period: string;
  onSelect: (id: string) => void;
}) {
  return (
    <section className="itinerary-list" aria-labelledby="list-heading">
      <h3 id="list-heading">Itineraries, by departure time</h3>
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
                <span>{timesText(it)}</span>
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
