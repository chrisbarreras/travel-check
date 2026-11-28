// "How the numbers work" (spec US4, FR-010): the method in plain language and every published
// definition verbatim, at ?view=method.
import type { ShowcaseIndex } from "@contract";
import { periodText } from "../format";
import { METHODOLOGY, REPOSITORY } from "../links";

export function MethodView({ index }: { index: ShowcaseIndex }) {
  const a = index.assumptions;
  return (
    <section className="method" aria-labelledby="method-heading">
      <p>
        <a href={import.meta.env.BASE_URL}>Back to the explorer</a>
      </p>
      <h2 id="method-heading">How the numbers work</h2>
      <p>
        Every figure is computed from the U.S. Bureau of Transportation Statistics&apos; on-time
        records for {periodText(index.period)}. For each one-stop itinerary and each day both of its
        flights were scheduled to connect, the pipeline takes the inbound flight&apos;s actual
        arrival and the outbound flight&apos;s actual departure. A day counts as worked when the gap
        was at least the minimum connection time ({a.min_connection_default_min} minutes, or{" "}
        {a.min_connection_partner_min} between partner airlines) plus a {a.boarding_cutoff_min}
        -minute boarding cutoff, and neither flight was cancelled or diverted.
      </p>
      <p>
        That is a historical frequency for the period, not a prediction, and not a count of
        passengers who missed connections. Below {a.min_sample_days} days there is no rate, only
        &quot;insufficient data&quot;. Differences between itineraries are given with 95% intervals
        over the days both flew. A faster itinerary is suggested only when its interval shows it was
        at most {Math.round(a.faster_margin * 100)} points worse.
      </p>
      <p>
        The full method, with its tests and limitations, is in the{" "}
        <a href={METHODOLOGY}>methodology</a>; the code is in the{" "}
        <a href={REPOSITORY}>repository</a>.
      </p>
      <h3>Definitions</h3>
      <dl className="method-definitions">
        {index.definitions.map((d) => (
          <div key={d.key}>
            <dt>
              {d.key.replaceAll("_", " ")} <code>{d.key}</code>
            </dt>
            <dd>
              {d.text}{" "}
              <a href={`${REPOSITORY}/blob/main/${d.methodology_anchor}`}>
                In the methodology
                <span className="visually-hidden"> ({d.key.replaceAll("_", " ")})</span>
              </a>
            </dd>
          </div>
        ))}
      </dl>
    </section>
  );
}
