# Feature Specification: Explorer Insights

**Feature Branch**: `005-explorer-insights`

**Created**: 2026-11-28

**Status**: Draft

**Input**: "Phase 1 feature explorer-insights from docs/roadmap.md: risk visuals, transfer-time slider, traveler-insight panels and 'Find this itinerary' links, landing example, 'How the numbers work' page." The owner asked for the remaining Phase 1 work to proceed with recommended decisions.

## Context

The explorer (feature 004) shows each showcase route's itineraries on a map, in a list and on a timeline, and each selected itinerary's rate with its definition. Feature 002 already publishes, for every itinerary:
- the per-day slack series (ADR-0006);
- the failure breakdown, monthly rates and disruption notes;
- the buffer, faster alternatives and connecting options;
- schedule warnings and "find" parameters.

This feature shows all of that. It ends Phase 1: after it, the deployed explorer meets the roadmap's Phase 1 scope.

## Clarifications

### Session 2026-11-28

The owner asked for recommended decisions to be adopted directly. Each answer below is the recommended option.

- Q: What does the transfer-time slider change? → A: The minimum connection time (the time needed between the inbound flight's arrival and the outbound flight's departure), from 15 to 120 minutes in 5-minute steps. The boarding cutoff stays at the published 15 minutes. The rate is recomputed in the browser from the published daily slack, with the shared test cases' rule (ADR-0006). The default is the itinerary's own published minimum connection time, so the default reproduces the published rate.
- Q: Does the slider's setting go in the address? → A: Yes, as `transfer=<minutes>` (ADR-0010). Moving it replaces the current history entry instead of adding one, and the parameter is left out at the default.
- Q: Where does "Find this itinerary" go? → A: A Google Flights search for the route and airline, prefilled as text (for example "Flights from LIT to LGA on Delta"), opened in a new tab. No date is set, no fare is fetched or stored, and the link says prices come from that site.
- Q: Where does "How the numbers work" live? → A: An in-app view at `?view=method`, linked from the header. Each definition links to its own section of docs/methodology.md, as since feature 003 (amended in review round 1: a second link in every definition would double the tab stops). It shows a plain-language summary and the published definitions verbatim, and links to docs/methodology.md for the full detail.
- Q: What does the monthly view show below the monthly minimum sample? → A: The month's day count with "too few days", never a bar height or percentage. Months with no flights show a dash. Disruption notes appear beside the chart, never inside the measured values.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Try a different transfer time (Priority: P1)

A traveler who needs more time to change planes, because of a checked bag, a terminal change or mobility, moves a slider for the time they need at the hub. The selected itinerary's "worked on X% of N days" updates at once for that time, with the same sample and period. The rate at the default setting matches the published rate exactly.

**Why this priority**: it turns a fixed number into an answer for the visitor's own situation. That is the reason the data is stored as daily slack, not as one rate (ADR-0006).

**Independent Test**: for every itinerary, the rate shown at the default setting equals the published rate. At several other settings, the shown rate equals the shared test cases' rule applied to the published daily series.

**Acceptance Scenarios**:

1. **Given** a selected itinerary, **When** the visitor moves the slider, **Then** the shown rate equals the share of the itinerary's paired days with slack at least the chosen time plus the boarding cutoff. Cancelled and diverted days count as not worked, and the rate is a whole percent of the same N days.
2. **Given** the default setting, **When** the itinerary is shown, **Then** the rate equals the published rate and the slider shows the itinerary's published minimum connection time.
3. **Given** a slider setting, **When** the address is copied and reopened, **Then** the same setting is shown. Moving the slider adds no history entries.
4. **Given** a below-minimum sample, **When** any setting is chosen, **Then** "insufficient data" is shown, never a percentage.
5. **Given** a keyboard or screen-reader user, **When** they use the slider, **Then** arrow keys change it in 5-minute steps, and its value and the resulting rate are announced.

---

### User Story 2 - See the shape of the risk (Priority: P1)

Next to the rate, a visitor sees:
- a reliability meter of 10 dots;
- a bar of why the connection didn't work (too little time, a cancelled leg, a diverted leg), with the counts in text;
- 12 monthly bars, each labelled with its value, with months below the monthly minimum shown as counts.

Known disruptions, such as the July 2024 CrowdStrike outage, appear as labelled notes beside the months they affected.

**Why this priority**: these visuals make the comparison understandable at a glance. Each is shown with its numbers, so nothing relies on the picture alone.

**Independent Test**: for each itinerary, the meter's filled dots, the failure bar's segments and counts, and the monthly bars, values and notes all equal the published data.

**Acceptance Scenarios**:

1. **Given** an itinerary with a rate, **When** it is shown, **Then** the meter fills the rate rounded to the nearest 10% of 10 dots, next to the exact text. The dots are hidden from screen readers; the text carries the meaning.
2. **Given** the failure breakdown, **When** it is shown, **Then** each failure type's segment is sized by its count and drawn with its own pattern, with the counts and labels in text and a sentence on what helps for the dominant type.
3. **Given** the monthly view, **When** it is shown, **Then** each month with a rate has a bar and a whole-percent label. A month below the monthly minimum shows its day count ("N d", with "N days, too few for a rate" for screen readers and a legend) and no bar; a month with no flights shows a dash. Each disruption note is listed separately, with its dates, text and source link, and its months are marked.

---

### User Story 3 - Traveler insights for the selected itinerary (Priority: P2)

Below the selected itinerary, panels answer the questions a traveler asks:
- **Faster, just as reliable:** a faster itinerary shown, by the paired interval, to be at most the margin worse, with the minutes saved, both rates and the interval.
- **Better connecting flight:** later outbound flights from the hub that worked more often for the same inbound flight, each with its rate and interval.
- **Buffer you needed:** the scheduled layover that would have left enough time on 95% of operated days, against this itinerary's.
- **Why it didn't work:** the failure bar.
- **By month:** the monthly view.
- **About this itinerary:** how often the two flights were scheduled to connect, schedule changes during the period, and how many sampled passengers flew this routing.

A panel with nothing to suggest says so plainly.

**Why this priority**: these turn the history into decisions. They come after the slider and visuals because each depends on the same rate presentation.

**Independent Test**: for each itinerary, each panel's content equals the published data. Panels with no data show their plain "none" text.

**Acceptance Scenarios**:

1. **Given** an itinerary with faster alternatives, **When** its panel is shown, **Then** each alternative shows its airline and hub, minutes saved, both rates with days, and the interval in points. Choosing it selects that itinerary on the route.
2. **Given** connecting options, **When** shown, **Then** each shows its outbound local departure, its rate with days, and its interval. Only options marked better are suggested; the rest are listed as other options.
3. **Given** the buffer, **When** shown, **Then** the needed layover, the itinerary's scheduled layover and the share of operated days with at least the needed layover are stated, with the share used (95%).
4. **Given** schedule changes, **When** shown, **Then** each change lists its date, the leg and the old and new local departure times.
5. **Given** a panel with nothing to show, **When** the itinerary is selected, **Then** the panel says so ("No faster itinerary was as reliable on this route").

---

### User Story 4 - Find this itinerary, and how the numbers work (Priority: P3)

From a selected itinerary, a visitor opens "Find this itinerary": a Google Flights search for the route and airline in a new tab. The link says prices come from that site and this app neither sees nor stores them. From the header or any definition, the visitor opens "How the numbers work": a plain-language view of the method, with every published definition and links to the full methodology.

**Why this priority**: closes the loop for a traveler, and gives a reviewer the method behind every number.

**Independent Test**: each itinerary's link opens the expected search address. The method view lists every published definition verbatim and is reachable from the header by keyboard.

**Acceptance Scenarios**:

1. **Given** a selected itinerary, **When** the visitor follows "Find this itinerary", **Then** a new tab opens on a Google Flights search naming the origin, destination and airline. The page states that prices come from that site.
2. **Given** the header link, **When** "How the numbers work" is opened, **Then** the view shows the summary, every published definition verbatim with its key, and links to docs/methodology.md. Back returns to the explorer.

### Edge Cases

- **Daily series with gaps:** cancelled or diverted days (null slack) count as not worked at every slider setting.
- **Slider below or above the data:** a setting where every or no day worked shows 100% or 0% with its days, never "insufficient data" unless the sample itself is below the minimum.
- **Months:** a month with no flights shows a dash; below the monthly minimum, it shows the count only.
- **Disruption notes:** a note's dates spanning two months mark both months. Notes are never used in any figure.
- **No faster alternatives, options or changes:** each panel says plainly that there are none.
- **A faster alternative on the same route:** choosing it selects it on the route, as from the list.
- **A two-airline itinerary:** the find link names both airlines.

## Requirements *(mandatory)*

### Functional Requirements

**Slider**

- **FR-001**: The selected itinerary MUST have a transfer-time control: the minimum connection time from 15 to 120 minutes in 5-minute steps, defaulting to its published minimum connection time.
- **FR-002**: The rate at a setting MUST be computed in the browser from the published daily series by the rule in `shared/test-cases/slack-feasibility.json`. The browser function MUST pass every shared test case (constitution, Principle II). At the default setting it MUST equal the published rate.
- **FR-003**: The setting MUST be in the address as `transfer`, replacing the current history entry. It is left out at the default, and invalid values fall back to the default silently.

**Risk visuals**

- **FR-004**: The reliability meter MUST follow docs/design.md: 10 dots, filled to the rate rounded to the nearest 10%, decorative, always next to the exact text rate. It MUST NOT be shown below the minimum sample.
- **FR-005**: The failure bar MUST show too little time (solid), cancelled (striped) and diverted (light), sized by their counts, with the counts in text.
- **FR-006**: The month chart MUST follow docs/design.md and the clarifications: 12 labelled bars, counts below the monthly minimum, dashes for no flights, and disruption notes separately with their sources.

**Insight panels**

- **FR-007**: The panels of User Story 3 MUST show the published faster alternatives, connecting options, buffer, failure breakdown, monthly view and schedule warnings for the selected itinerary. Each figure has its definition from the index, its sample and the period (constitution, Principle I).
- **FR-008**: Suggestions MUST appear only where the data marks them: faster alternatives as published, and connecting options with `better` true. Every suggestion states its evidence (interval and days).

**Links and method**

- **FR-009**: "Find this itinerary" MUST open a Google Flights search, prefilled with origin, destination and airline names, in a new tab. It carries `rel="noopener"` and a note that prices come from that site.
- **FR-010**: "How the numbers work" MUST be an in-app view at `?view=method`, listing every published definition verbatim with links to docs/methodology.md. It is linked from the header and reachable by keyboard.

**Checks**

- **FR-011**: The features of feature 003 and 004 MUST stay covered. New pure functions (slider rate, meter fill, month layout, find URL) are written test-first. The slider rate passes every shared test case. End-to-end tests check every itinerary at the default setting and at least two others. Visual references cover the new panels at 360 and 1280 px. axe and keyboard tests cover the slider, panels and method view.
- **FR-012**: Budgets stay: first-view scripts at most 150 KB gzip, map scripts at most 300 KB gzip, Lighthouse mobile performance at least 0.90 and accessibility 1.00.

### Key Entities

All are published by feature 002 and validated by the existing data module: the daily series, the failure breakdown, monthly rates and disruption notes, the buffer, faster alternatives, connecting options, schedule warnings and find parameters. This feature adds no data.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For all 144 published itineraries, the slider's rate at the default setting equals the published rate, checked automatically.
- **SC-002**: The browser's slider rate passes 100% of the shared test cases.
- **SC-003**: For every itinerary, the meter, failure bar, month chart and panels match the published data, checked automatically.
- **SC-004**: Zero WCAG 2.2 AA violations at 360 and 1280 px with a selected itinerary and its panels open. The slider, panels and method view are fully operable by keyboard in the scripted tests.
- **SC-005**: The budgets of FR-012 hold.

## Out of Scope

- Changing any published figure or the data contract, or new pipeline computations.
- Fares, live data, accounts and search beyond the 12 showcase routes (Phase 2).
- A slider for the boarding cutoff. It stays at the published 15 minutes.

## Assumptions

- **Charts:** drawn as plain HTML and CSS, or small inline SVG. ADR-0002's chart libraries are unnecessary for one bar and 12 small bars, and ADR-0016's plain-CSS decision applies. The planning step confirms this.
- **Google Flights link:** the text-query search address (`https://www.google.com/travel/flights?q=...`) is used. If it stops working, the link degrades to a plain Google Flights home link with the same note.
