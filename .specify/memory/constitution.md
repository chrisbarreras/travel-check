# Flight App Constitution

Flight App is a map-first explorer that compares the reliability of flight itineraries using
real historical on-time data. It is a portfolio-first full-stack project; commercial potential is
secondary.

## Core Principles

### I. Statistical Honesty (NON-NEGOTIABLE)

- Every number shown to users MUST have a written definition, a sample size and a data period.
- Connection success, on-time arrival, cancellation and recovery MUST remain separate measures.
  They MUST NOT be merged into a single opaque score.
- When a sample is below the configured minimum size, the UI MUST show "insufficient data" instead
  of a rate. Values MUST NOT be displayed with more precision than the data supports.
- Below the minimum sample, the UI MAY give honest small-sample feedback as raw observed counts
  (for example "didn't work on 4 of the 7 days we saw"), but only when all of these hold:
  - the number of observed days is at least the configured small-sample floor;
  - the statement is labelled as a small sample that is too small for a rate;
  - it is shown with a plain-language uncertainty range for how often it would happen (for
    example "roughly between 3 and 8 in 10 days");
  - it is never expressed as a single percentage, and never ranked, compared with other results,
    or used to qualify a showcase example, a suggestion or a go/no-go criterion.
- Results MUST be described as connection feasibility, never as observed passenger outcomes
  (ADR-0005).
- Model claims MUST be backed by chronological holdout testing, with calibration results published
  in `docs/methodology.md`.

**Rationale:** the product's entire value is trustworthy reliability numbers. A precise-looking
but unsupported number is worse than no number. Hiding a small but clear pattern is also a
failure of honesty, so a few observed days may be reported as what they are: a count, labelled
as too few for a rate, with its uncertainty.

### II. Automated Verification (NON-NEGOTIABLE)

- Calculation, pipeline, time-zone and schema code MUST be written test-first: a failing test,
  then the code that makes it pass.
- All other code, including UI, MUST ship with its automated tests in the same change.
- Manual testing MUST NOT be part of any definition of done.
- Each feature's tasks MUST include the applicable checks: unit, component, end-to-end
  (Playwright), visual regression (Playwright screenshots run in Docker), accessibility (axe-core
  plus scripted keyboard tests) and performance (Lighthouse CI, bundle and data size limits).
- Calculations that run in both the browser and the API MUST share one set of test cases.
- Map logic MUST live in pure, unit-tested functions. Map end-to-end tests MUST assert rendered
  features, not only pixels.
- Visual reference images MUST change only through a deliberate, reviewed update.
- Tests MUST be deterministic and MUST NOT depend on the network.

**Rationale:** calculation bugs silently corrupt every number shown, and a fully automated suite
lets every change be verified without manual effort.

### III. Thin, Deployable Slices

- Work MUST follow the phases in `docs/roadmap.md`, one phase at a time.
- Every spec MUST include an out-of-scope list. New ideas go to the roadmap backlog, not into the
  current feature.
- A phase is done only when its README and docs are updated and, if the phase has a deployable
  deliverable (a site, API or service), that deliverable is deployed. Phases without one, such as
  analysis-only experiments, are done when their roadmap exit criterion is met.

**Rationale:** a finished, deployed slice is worth more than an ambitious unfinished system,
especially for a portfolio.

### IV. One Data Contract

- Pydantic models MUST be the only definition of data shapes (ADR-0007).
- TypeScript types MUST be generated from those models and never written by hand. CI MUST fail
  when generated types are out of date.
- All times MUST be stored and computed in UTC and converted to local time only for display
  (ADR-0008).

**Rationale:** one definition prevents the pipeline, API and frontend from drifting apart, and
UTC prevents silent errors across time zones and midnight.

### V. Accessible and Clear by Default

- Risk MUST NOT be conveyed by color alone; it MUST also have a text label or icon.
- Every interaction MUST work with the keyboard, and controls MUST have screen-reader labels.
- Layouts MUST work on phone-sized screens.
- Every value MUST state what it means and how fresh its data is.
- Each phase MUST set a performance budget covering load time and data size (ADR-0009).

**Rationale:** clarity and accessibility are part of correctness for a decision-support tool,
and reviewers often open the demo on a phone.

### VI. Simplicity with Replaceable Providers

- Build the simplest thing that meets the spec. Any added complexity MUST be justified in the
  plan's Complexity Tracking section.
- Every external data source MUST sit behind a provider interface, so a licensed provider can
  replace a free one without changing callers.
- Tools listed as avoided in ADR-0002 MUST NOT be introduced unless a measured need is recorded.

**Rationale:** simplicity keeps the project finishable; provider interfaces keep the commercial
path open.

## Data and Technology Constraints

- Technology choices MUST follow the ADRs in `docs/adr/`. Changing one requires a new ADR that
  supersedes it.
- Only free data sources may be used until Phase 5.
- Data licenses MUST be respected, and required attributions (for example BTS, airportsdata and
  the basemap provider) MUST be displayed.
- Secrets, credentials and personal data MUST NOT be committed to the repository.
- Raw data MUST stay out of git. The pipeline MUST be able to rebuild all derived data from pinned
  configuration.

## Development Workflow and Quality Gates

- Each feature MUST be developed on its own git branch and follow the cycle
  specify → clarify → plan → tasks → analyze → implement.
- The human owner MUST review and approve the spec and the implementation plan before
  implementation starts.
- **Independent review (NON-NEGOTIABLE).** Before a feature merges:
  1. A new `feature-reviewer` agent (`.claude/agents/feature-reviewer.md`) with no prior context
     MUST review the branch against `main`. It receives only the feature directory and base
     branch, never the implementer's summary.
  2. Its report MUST be saved and committed as `specs/NNN-name/review.md`.
  3. All BLOCKING findings MUST be fixed. SHOULD-FIX findings MUST be fixed or answered in
     writing in `review.md`.
  4. After fixes, another new reviewer (never the previous one) MUST re-review, repeating until
     the verdict is APPROVE.
  5. The human owner reads the review report and makes the merge decision.
- Before merging, the full automated suite (tests, lint, type checks, generated-types check) MUST
  pass, and affected docs (methodology, architecture, README, ADRs) MUST be updated.
- Spec files MUST be committed together with the code they describe.

## Governance

- This constitution overrides all other project practices. When an ADR or spec conflicts with it,
  either the constitution is amended or the conflicting document changes.
- Amendments MUST be made in a commit that explains the reason and bumps the version using
  semantic versioning: MAJOR for removing or redefining a principle, MINOR for adding a principle
  or section or materially expanding guidance, PATCH for clarifications and wording.
- Every implementation plan's Constitution Check MUST pass or record a justified exception in its
  Complexity Tracking section.
- The independent reviewer MUST check compliance with every principle for each feature.

**Version**: 1.2.0 | **Ratified**: 2026-11-24 | **Last Amended**: 2026-11-25
