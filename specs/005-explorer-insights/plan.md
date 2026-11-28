# Implementation Plan: Explorer Insights

**Branch**: `005-explorer-insights` (from `004-explorer-core`, which is awaiting merge) | **Date**: 2026-11-28 | **Spec**: [spec.md](spec.md)

**Approval**: the owner's standing instruction of 2026-11-28 approves this spec and plan (as for feature 004). The merge decision stays with the owner.

## Summary

The selected itinerary gains:
- a transfer-time slider that recomputes its rate in the browser from the published daily slack, with the shared test cases' rule;
- a reliability meter, failure bar and month chart with disruption notes;
- six traveler-insight panels;
- a "Find this itinerary" link.

A "How the numbers work" view lists every published definition. All of it is display of data feature 002 already publishes: no pipeline or contract change.

## Technical Context

- **Stack:** unchanged (React 19, TypeScript, Vite; the tests of features 003 and 004).
- **New dependencies:** none. The charts are HTML and CSS (ADR-0016). The slider is a native range input.
- **Pure functions, test-first:**
  - `slackRate(daily, transferMin, cutoffMin, minSample)`, against `shared/test-cases/slack-feasibility.json`;
  - `meterDots(rate)`;
  - `monthBars(monthly, notes)`;
  - `findUrl(find, airlineNames)`;
  - `parseTransfer` and `serializeTransfer` for the address.
- **Budgets:** first-view scripts at most 150 KB gzip (today 91 KB). The insight panels are small, so no extra lazy chunk is planned.

## Constitution Check

| Principle | Status | How |
|---|---|---|
| I. Statistical honesty | Pass | Every new figure carries its published definition, sample and period. Below the minimum sample: no meter, no percentage, counts only (monthly). Suggestions only where the data marks them, with their intervals. Disruption notes are kept apart from measured values |
| II. Automated verification | Pass | The slider rate is test-first against the shared cases (the same cases the pipeline passes). Every itinerary is checked at the default setting against the published rate. Visual, axe and keyboard tests cover the new controls |
| III. Thin slices | Pass | It completes Phase 1's scope; the roadmap row is marked at merge |
| IV. One data contract | Pass | No new shapes. Types come from `@contract` |
| V. Accessible and clear | Pass | Meter dots are decorative next to text; the failure bar uses patterns plus counts; month bars are labelled; the slider is a native range input with a live result |
| VI. Simplicity | Pass | No chart library: ADR-0016's plain CSS covers one bar and 12 small bars |

## Structure

```text
web/src/insights/   slackRate.ts, meter.ts, months.ts, find.ts (pure)
                    TransferSlider, Meter, FailureBar, MonthChart, panels/*, InsightPanels
web/src/method/     MethodView (?view=method)
web/src/selection/  + transfer parameter
web/tests/unit/     slack-rate (shared cases), meter, months, find, transfer url
web/tests/component insights panels, slider
web/tests/e2e       every itinerary at the default and two settings; panels match data
```

## Complexity Tracking

None.
