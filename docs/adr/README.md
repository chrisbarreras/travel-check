# Architecture Decision Records

Each record captures one lasting decision: the context, what was decided, and the consequences. Decisions that apply to a single feature belong in that feature's Spec Kit `research.md` instead.

To change a decision, add a new ADR that supersedes the old one, and set the old one's status to `Superseded by ADR-NNNN`. Don't rewrite history.

| ADR | Decision | Status |
|---|---|---|
| [0001](0001-static-first-delivery.md) | Ship a static site first; add the API in Phase 2 | Accepted |
| [0002](0002-technology-stack.md) | Technology stack | Accepted; frontend hosting superseded by 0015, styling and data fetching by 0016 |
| [0003](0003-duckdb-parquet-before-postgres.md) | DuckDB/Parquet for v1; Postgres only once user data exists | Accepted |
| [0004](0004-itinerary-definition.md) | What counts as an itinerary | Accepted; recurrence superseded by 0013, identity and layover application by 0014 |
| [0005](0005-connection-outcome-label.md) | Connection outcome label and same-day delay pairing | Accepted |
| [0006](0006-risk-as-slack-distributions.md) | Store risk as slack distributions, not single probabilities | Accepted |
| [0007](0007-pydantic-schema-source-of-truth.md) | Pydantic models are the single definition of the data shape | Accepted |
| [0008](0008-utc-time-handling.md) | Store times in UTC; convert to local only for display | Accepted |
| [0009](0009-data-storage-and-git.md) | Raw data stays out of git; small derived data is committed | Accepted |
| [0010](0010-url-selection-state.md) | The current selection lives in the URL | Accepted |
| [0011](0011-airport-timezone-source.md) | Use the airportsdata package for airport time zones (supersedes the source in 0008) | Accepted |
| [0012](0012-phase0-go-no-go.md) | Phase 0 go/no-go: GO | Accepted |
| [0013](0013-sold-routings-and-connection-recurrence.md) | Itineraries must be sold routings (DB1B) that actually connect | Accepted; identity superseded by 0014 |
| [0014](0014-schedule-slot-itinerary-identity.md) | Identify itineraries by schedule slot; apply layover limits per day | Accepted |
| [0015](0015-static-hosting-github-pages.md) | Host the static site on GitHub Pages; block merges with a ruleset | Accepted |
| [0016](0016-plain-css-and-own-data-hook.md) | Plain CSS with design tokens and no data-fetching library, until a measured need | Accepted |

## Template

```markdown
# ADR-NNNN: Title

- **Status:** Proposed | Accepted | Superseded by ADR-NNNN
- **Date:** YYYY-MM-DD

## Context
What problem or constraint forces a decision.

## Decision
What we will do.

## Consequences
What becomes easier, what becomes harder, and what we accept.
```
