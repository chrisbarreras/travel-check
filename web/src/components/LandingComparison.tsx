import type { LandingView } from "../data";
import { periodText, similarOrMore } from "../format";
import { Definition } from "./Definition";
import { Difference } from "./Difference";
import { ItineraryCard, itineraryName as name } from "./ItineraryCard";

/** The landing comparison: two itineraries on one route, and how often each worked. */
export function LandingComparison({ view }: { view: LandingView }) {
  const { index, comparison, a, b } = view;
  const period = periodText(view.landing.period);
  // Below the minimum sample an itinerary is never ranked or compared (constitution, I).
  const comparable = a.result.status === "ok" && b.result.status === "ok";
  const verdict = comparable ? similarOrMore(comparison.ci_low, comparison.ci_high) : null;
  const definition = (key: string) => index.definitions.find((d) => d.key === key);
  return (
    <section className="comparison" aria-labelledby="route-heading">
      <h2 id="route-heading">
        {a.find.origin} to {a.find.dest}
      </h2>
      <p className="muted">Two one-stop itineraries on the same route, {period}.</p>
      <p className="summary">
        {verdict === "more" ? `${name(a)} worked more often than ${name(b)}.` : null}
        {verdict === "similar"
          ? `${name(a)} and ${name(b)} worked on a similar share of days.`
          : null}
        {verdict === null
          ? `One of these itineraries has too few days for a rate (fewer than ${String(
              index.assumptions.min_sample_days,
            )}), so the two are not compared.`
          : null}
      </p>
      <div className="cards">
        <ItineraryCard
          itinerary={a}
          headingId="itinerary-a"
          period={period}
          badge={verdict === "more" ? "Worked more often" : undefined}
        />
        <ItineraryCard itinerary={b} headingId="itinerary-b" period={period} />
      </div>
      {comparable ? <Difference comparison={comparison} /> : null}
      <div className="definitions">
        <Definition
          summary="What “worked” means"
          definition={definition("connection_feasibility")}
        />
        <Definition summary="Which days count" definition={definition("paired_days")} />
        {comparable ? null : (
          <Definition
            summary="What “insufficient data” means"
            definition={definition("insufficient_data")}
          />
        )}
        {comparable ? (
          <Definition
            summary="How the difference is measured"
            definition={definition("comparison_difference")}
          />
        ) : null}
        <Definition summary="Layover" definition={definition("layover")} />
        <Definition summary="Travel time" definition={definition("travel_time")} />
      </div>
    </section>
  );
}
