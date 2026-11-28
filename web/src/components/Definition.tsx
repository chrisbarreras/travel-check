import type { Definition as DefinitionRecord } from "@contract";
import { REPOSITORY } from "../links";

/** A published definition, verbatim, in a native disclosure (FR-004, FR-010). */
export function Definition({
  summary,
  definition,
}: {
  summary: string;
  definition: DefinitionRecord | undefined;
}) {
  if (!definition) return null;
  return (
    <details className="definition">
      <summary>{summary}</summary>
      <p>{definition.text}</p>
      <p className="links">
        <a href={`${REPOSITORY}/blob/main/${definition.methodology_anchor}`}>
          How this is computed<span className="visually-hidden"> ({summary.toLowerCase()})</span>
        </a>
      </p>
    </details>
  );
}
