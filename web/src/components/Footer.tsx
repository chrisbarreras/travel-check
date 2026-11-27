import type { ShowcaseIndex } from "@contract";
import { builtDate, periodText } from "../format";
import { METHODOLOGY, REPOSITORY } from "../links";

/**
 * Sources, freshness and links (FR-006, FR-007). Shown in every state; the data part (period,
 * build date, attributions) only once the data has loaded.
 */
export function Footer({ index, builtAt }: { index?: ShowcaseIndex; builtAt?: string }) {
  return (
    <footer className="footer">
      {index && builtAt ? (
        <>
          <p>
            Data period {periodText(index.period)}. Data built {builtDate(builtAt)}.
          </p>
          <ul className="attributions">
            {index.attribution.map((a) => (
              <li key={a.source}>
                {a.text} <a href={a.url}>{a.source}</a> ({a.licence}).
              </li>
            ))}
          </ul>
        </>
      ) : null}
      <ul className="links">
        <li>
          <a href={METHODOLOGY}>How the numbers work (methodology)</a>
        </li>
        <li>
          <a href={REPOSITORY}>Source code</a>
        </li>
      </ul>
      <p>
        Fonts: Inter and Space Grotesk, SIL Open Font License. © 2026 Christopher T. Barreras
        Consulting. All rights reserved.
      </p>
    </footer>
  );
}
