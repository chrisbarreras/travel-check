import type { ShowcaseComparison } from "@contract";
import { intervalText, points, signed, similarOrMore } from "../format";

/** The difference between the two itineraries, with its interval and sample. */
export function Difference({ comparison }: { comparison: ShowcaseComparison }) {
  const verdict = similarOrMore(comparison.ci_low, comparison.ci_high);
  return (
    <section className="difference" aria-labelledby="difference-heading">
      <h3 id="difference-heading">The difference</h3>
      <p className="difference-value">{signed(points(comparison.difference))} points</p>
      <p>
        {intervalText(comparison.ci_low, comparison.ci_high)}, over {comparison.shared_days} days
        both flew.
        {verdict === "similar"
          ? " The interval includes zero, so the two worked on a similar share of days."
          : null}
      </p>
    </section>
  );
}
