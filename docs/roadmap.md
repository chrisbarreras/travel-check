# Roadmap

How the flight intelligence app grows from a static showcase into a full-stack product. The long-term vision lives in [flight_intelligence_product_design.md](../flight_intelligence_product_design.md). This document decides **what gets built, in what order, and when each phase is done**.

## Goals

1. **Primary:** a polished, deployed full-stack portfolio project.
2. **Secondary:** a credible foundation for a commercial product.

## Ground rules for every phase

- **Each phase ships.** It ends deployed, with an updated README, so the project is always presentable.
- **One phase at a time.** Ideas for later phases go in the backlog at the bottom, not into the current phase.
- **Phases are built as Spec Kit features.** Each feature runs `/speckit-specify` → `/speckit-clarify` → `/speckit-plan` → `/speckit-tasks` → `/speckit-analyze` → `/speckit-implement`, and its spec lists what is out of scope.
- **Every feature is independently reviewed before merging** by a new `feature-reviewer` agent with no prior context ([.claude/agents/feature-reviewer.md](../.claude/agents/feature-reviewer.md)).

**Feature count:** 9 features for the portfolio core (Phases 0–3), 10 through Phase 4. Each feature has one spec, one implementation plan and one task list.
- **Free data only until Phase 5.** Use BTS on-time data, schedules derived from it, and OpenSky. No paid APIs.
- **Statistical honesty.** Every number shown has a defined meaning, a sample size and a data period. Sparse data shows "insufficient data" instead of a number.

---

## Phase 0: Data feasibility check

**Goal:** confirm, using real BTS data, that reliability differences between realistic itineraries are large enough to be worth showing.

**Status:** complete. Decision **GO** ([ADR-0012](adr/0012-phase0-go-no-go.md)). 81 showcase examples in 9 origin/destination pairs across 5 hubs, every itinerary a routing sold in DB1B whose flights connect on at least 60% of days ([ADR-0013](adr/0013-sold-routings-and-connection-recurrence.md)). Data: July 2024 to June 2025, 12 months so seasonal weather could be measured (scope grew from "a few months").

**Scope**
- Download a few months of BTS on-time data for 5–8 hubs.
- Build itineraries using the rules in [ADR-0004](adr/0004-itinerary-definition.md).
- Compute the connection outcome label and same-day delay pairing from [ADR-0005](adr/0005-connection-outcome-label.md) for 10–15 origin/destination pairs.
- Test how sensitive results are to the minimum connection time, boarding cutoff and recurrence threshold.
- Write a notebook with results and a first look at sample sizes.

**Exit criteria**
- At least a few itinerary pairs show a meaningful reliability gap, which become the showcase examples.
- A go/no-go decision is recorded in an ADR.

**Spec Kit features:** `bts-connection-experiment`

---

## Phase 1: Static showcase explorer ← first deployed milestone

**Goal:** a visually striking, real-data demo that a reviewer understands within seconds.

**Scope**
- A Python pipeline that precomputes curated itineraries and statistics into static JSON, validated against Pydantic models that the future API will reuse ([ADR-0007](adr/0007-pydantic-schema-source-of-truth.md)), with TypeScript types generated from them.
- A React + Vite + MapLibre frontend with:
  - a map with curved route lines, an itinerary list and a timeline, with selection kept in sync
  - risk badges and delay-distribution visuals, with risk never shown by color alone
  - a transfer-time slider that recomputes connection risk in the browser from stored slack distributions ([ADR-0006](adr/0006-risk-as-slack-distributions.md))
  - the selection stored in the URL, so links open on a specific example ([ADR-0010](adr/0010-url-selection-state.md))
  - a landing view that opens on one striking example
  - a layout that works on phones
- A "How the numbers work" page (first version of `docs/methodology.md`).
- Deployment as a static site; a README with a GIF and the live link.

**Out of scope:** API, arbitrary search, accounts, live data, recovery routes.

**Exit criteria**
- The site is live, loads fast and works on phones.
- Every number on screen traces back to the pipeline output.
- The README has a GIF, the link and a methodology summary.

**Spec Kit features**

| Feature | Delivers |
|---|---|
| `showcase-data-pipeline` | BTS → itineraries → slack distributions → validated JSON; Pydantic models and generated TypeScript types |
| `web-foundation` | Vite/React scaffold, the full automated test setup (unit, component, Playwright end-to-end and visual in Docker, axe, Lighthouse CI), CI that blocks merges on failure, and a deployed placeholder page |
| `explorer-core` | Map, list and timeline with synced selection; selection in the URL. Deployable on its own |
| `explorer-insights` | Risk visuals, transfer-time slider, landing example, "How the numbers work" page |

---

## Phase 2: API and interactive analysis

**Goal:** turn the static demo into a full-stack app where users explore any covered route instead of only curated examples.

**Scope**
- A FastAPI backend reading precomputed DuckDB/Parquet data and serving the same response shape as the Phase 1 JSON.
- A TypeScript client generated from the API schema (`openapi-typescript`), so frontend and backend share types.
- Search across any origin/destination pair among the covered airports.
- Connection-risk calculation moves to the API, using the same method and shared test cases as the Phase 1 browser version.
- More hubs and a longer data period.
- GitHub Actions CI running tests, type checks and builds; the API deployed as a container.

**Exit criteria**
- The frontend runs entirely on the API, with no static JSON left.
- CI passes on every push; the API meets its response-time target for covered routes.

**Spec Kit features:** `risk-api`, `route-search`

---

## Phase 3: Recovery and model rigor

**Goal:** add the product's second key differentiator, recovery, and make the model's accuracy checkable.

**Scope**
- A recovery engine: a time-dependent graph that finds later feasible routes after a missed connection, built as a custom search rather than with networkx.
- Last-flight-of-day risk and expected delay if the connection is missed.
- Chronological holdout testing (for example, train 2023–2024, test 2025), calibration plots and a Brier score.
- Fallback to broader data groups when samples are small, with a minimum sample size.
- Full `docs/methodology.md` with results and known limitations.

**Exit criteria**
- Calibration results are published in the methodology, including where the model is weak.
- Two itineraries with similar connection odds but different recovery options are shown differently.

**Spec Kit features:** `recovery-engine`, `model-validation`

---

## Phase 4: Live flight slice (optional)

**Goal:** demonstrate real-time engineering with free data.

**Scope**
- A "track this flight" page using OpenSky Network positions, which allows non-commercial use.
- Live connection-risk updates for a tracked connection, with data freshness shown.
- Polling that speeds up near departure and stops after arrival; a clear stale-data state.

**Exit criteria**
- One live flight can be tracked end to end, and stale or missing data is handled visibly.

**Spec Kit features:** `live-flight-tracking`

---

## Phase 5: Commercial exploration (optional)

**Goal:** test whether a commercial product is viable, only after the portfolio phases are done.

**Candidate scope (decide after Phases 0–3)**
- Accounts and saved trips, adding Postgres for user data.
- Alerts for tracked trips.
- A browser extension that adds risk ratings to existing flight search sites.
- Fare data from a licensed provider (written data-rights terms required first).
- User interviews and a willingness-to-pay test.

**Exit criteria:** defined when this phase starts.

---

## Supporting documents

| Document | Purpose | Started in |
|---|---|---|
| `.specify/memory/constitution.md` | Project-wide rules for all specs | Before Phase 0 |
| `docs/design.md` | Visual direction: palette, typography, map style, motion, accessibility | Before Phase 1 |
| `docs/architecture.md` | One-page system overview and data flow | Phase 1 |
| [`docs/adr/`](adr/README.md) | Lasting decisions; ADR-0001 to 0010 recorded before Phase 0 | Before Phase 0 |
| `docs/methodology.md` | How every number is computed, plus validation results | Phase 1 (first version), Phase 3 (full) |

## Backlog (not assigned to a phase)

- Phase 0 follow-ups from the final review (review.md, round 11): a test that `verify` fails on a hand-edited committed report or a changed config/package; days at the end of the period whose outbound falls past the loaded data should be excluded rather than counted as not connecting; label the notebook's sold-passenger column as a routing total; let `verify` extract DB1B into its temporary directory; run the forbidden-wording check on the whole summary; include code identity in the manifest's runtime provenance

- International routes and itineraries with two or more stops
- Nearby alternate airports in recovery options
- Personalized transfer assumptions (mobility needs, checked bags, separate tickets)
- Weather and FAA airport-status overlays
