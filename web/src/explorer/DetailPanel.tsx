import type { ShowcaseIndex, ShowcaseItinerary } from "@contract";
import { Definition } from "../components/Definition";
import { ItineraryCard } from "../components/ItineraryCard";

/** The selected itinerary, with every figure's definition (FR-009). */
export function DetailPanel({
  itinerary,
  index,
  period,
}: {
  itinerary: ShowcaseItinerary;
  index: ShowcaseIndex;
  period: string;
}) {
  const definition = (key: string) => index.definitions.find((d) => d.key === key);
  return (
    <section className="detail" aria-labelledby="detail-itinerary">
      <div className="cards single">
        <ItineraryCard
          itinerary={itinerary}
          headingId="detail-itinerary"
          period={period}
          badge={itinerary.tight_layover ? "Tight layover" : undefined}
          emphasis={false}
          badgeTone="warn"
        />
      </div>
      <div className="definitions">
        <Definition
          summary="What “worked” means"
          definition={definition("connection_feasibility")}
        />
        <Definition summary="Which days count" definition={definition("paired_days")} />
        {itinerary.result.status === "insufficient_data" ? (
          <Definition
            summary="What “insufficient data” means"
            definition={definition("insufficient_data")}
          />
        ) : null}
        {itinerary.tight_layover ? (
          <Definition summary="Tight layover" definition={definition("tight_layover")} />
        ) : null}
        <Definition summary="Layover" definition={definition("layover")} />
        <Definition summary="Travel time" definition={definition("travel_time")} />
      </div>
    </section>
  );
}
