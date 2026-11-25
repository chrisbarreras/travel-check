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
- Fare data from a licensed provider (written data-rights terms required first). Options, from least to most commitment:
  - affiliate or metasearch APIs (for example Skyscanner partner API, Kayak affiliate, Travelpayouts): fares or cached fares, booking happens elsewhere; partner approval needed and terms limit how prices are stored and shown
  - booking APIs that aggregate airline content (for example Duffel, Travelfusion): live offers with exact flight numbers, fares and baggage rules, and booking; the app becomes a seller of travel (payments, card-data security, refunds, schedule changes, customer service, state seller-of-travel registration)
  - global distribution systems (Amadeus, Sabre, Travelport): the broadest content; production access normally needs travel-agency accreditation (IATA or ARC) and commercial contracts
  - never scraping airline or metasearch sites (terms of service, and the constitution's data-licence rule)

  Recommended start: an affiliate or metasearch API for prices; a booking API only if user research shows people want to book in the app. Fare offers carry flight numbers, so they join directly to the reliability data (for example "this ticket costs $20 more and connects far more often"); offers with no matching history must say so.
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

- **Faster alternatives with no worse connection feasibility.** For a chosen itinerary, show comparable itineraries that are meaningfully shorter and whose connection feasibility is shown, by the paired confidence interval, to be no more than a set margin worse (for example 2 or 5 points). This is an equivalence test, not merely "no significant difference". Phase 0 data already supports it: within the 15 analyzed markets, 58 comparable pairs save 30 minutes or more with the shorter itinerary at most 2 points worse (49 of them robust to every assumption scenario). Needs: comparability no longer capped at 60 minutes of travel-time difference, the margin as a configured and documented threshold, and the interval shown with every suggestion, not just a verdict. Candidate phases: curated examples in Phase 1 (`explorer-insights`), any covered route with Phase 2 `route-search`
- **Which connecting flight to take.** Within one route, airline and hub, the choice of connecting flight changes connection feasibility a lot (LGA-ATL-MCO on Delta: 72% to 97% across flight pairs). Rank the outbound options at the hub for a given inbound flight. Needs: data already in the itinerary results
- **Time-of-day guidance.** Phase 0: connections whose first flight leaves before 10:00 were feasible on 93% of days, 10:00-15:00 on 92%, after 15:00 on 84% (235 itineraries, mostly Delta). Show "earlier connections are more reliable on this route" only where the route's own data supports it. Needs: a per-route test before any advice is shown, since the Phase 0 figure is an association across markets
- **Seasonal and event view.** Feasibility by month was mostly 92-94% but 83% in July 2024 (7.6% of days cancelled, likely the CrowdStrike outage that hit Delta), 88% in January 2025 (likely winter storms) and 3.4% cancelled in October 2024 (likely Hurricane Milton in Orlando markets). Show each connection's monthly pattern, and flag when a single event dominates a year. Needs: monthly results per itinerary, event labels kept separate from the measured numbers
- **Advice by failure type.** Of 6,027 failed connection days in Phase 0, 74% had too little time, 21% a cancellation, 4% a diversion. Say which risk dominates for each itinerary and what helps (a longer layover or another outbound for time; rebooking options for cancellations, with Phase 3 recovery). Needs: the separate failure counts, already computed
- **Buffer recommendation.** From each itinerary's slack distribution, state the layover needed to have connected on, for example, 95% of days. Closely related to the Phase 1 transfer-time slider ([ADR-0006](adr/0006-risk-as-slack-distributions.md)); phrased as a recommendation. Needs: slack distributions, already stored
- **"Find this itinerary" deep links.** A button on each itinerary that opens a prefilled search (route, date, flight numbers) on Google Flights or the airline's site. Free, needs no fare data, contract or licence, and lets travelers see real prices and book where they usually do; the app never sees prices. Candidate: Phase 1 `explorer-insights`
- **Check an itinerary found on another site.** Entry points, simplest first: a paste box that reads flight numbers, airports and date from copied text or a confirmation email; a link format such as `/check?flights=DL988,DL1497&date=2025-03-14` (selection in the URL, [ADR-0010](adr/0010-url-selection-state.md)); a bookmarklet that reads the current page; the Phase 5 browser extension adding a "Check reliability" button to search results; sharing from a phone when installed as a web app; trip import by forwarded email or TripIt (needs accounts); links or embedded badges from partner sites. Must handle codeshare numbers (foreign marketing numbers are not in BTS data), flights with no history in the data period (new, renumbered or changed: say so, never guess), and future dates (compare with history only). Candidate: paste box and link format with Phase 2 `route-search`; bookmarklet as a cheap test before the extension
- **Schedule-pattern warnings.** Flag connections that exist only on some days (connection share below 100%) and connections whose flights changed schedule during the period, so travelers aren't surprised when booking. Needs: daily schedule matching, already used for connection-level recurrence
- International routes and itineraries with two or more stops
- Nearby alternate airports in recovery options
- Personalized transfer assumptions (mobility needs, checked bags, separate tickets)
- Weather and FAA airport-status overlays
