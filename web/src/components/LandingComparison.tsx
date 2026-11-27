import type { LandingView } from "../data";
import { airlineName, periodText, similarOrMore } from "../format";
import { Definition } from "./Definition";
import { Difference } from "./Difference";
import { ItineraryCard } from "./ItineraryCard";

/** The landing comparison: two itineraries on one route, and how often each worked. */
export function LandingComparison({ view }: { view: LandingView }) {
  const { index, comparison, a, b } = view;
  const verdict = similarOrMore(comparison.ci_low, comparison.ci_high);
  const name = (i: typeof a) => `${airlineName(i.airline)} via ${i.hub}`;
  const definition = (key: string) => index.definitions.find((d) => d.key === key);
  return (
    <section className="comparison" aria-labelledby="route-heading">
      <h2 id="route-heading">
        {a.find.origin} to {a.find.dest}
      </h2>
      <p className="muted">
        Two one-stop itineraries on the same route, {periodText(view.landing.period)}.
      </p>
      <p className="summary">
        {verdict === "more"
          ? `${name(a)} worked more often than ${name(b)}.`
          : `${name(a)} and ${name(b)} worked on a similar share of days.`}
      </p>
      <div className="cards">
        <ItineraryCard
          itinerary={a}
          headingId="itinerary-a"
          badge={undefined}
        />
        <ItineraryCard itinerary={b} headingId="itinerary-b" />
      </div>
      <Difference comparison={comparison} />
      <div className="definitions">
        <Definition
          summary="What “worked” means"
          definition={definition("connection_feasibility")}
        />
        <Definition summary="Which days count" definition={definition("paired_days")} />
        <Definition
          summary="How the difference is measured"
          definition={definition("comparison_difference")}
        />
        <Definition summary="Layover" definition={definition("layover")} />
        <Definition summary="Travel time" definition={definition("travel_time")} />
      </div>
    </section>
  );
}
