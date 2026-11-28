---
description: "Task list for the explorer insights"
---

# Tasks: Explorer Insights

**Input**: [spec.md](spec.md), [plan.md](plan.md)

**Tests**: required.
- Pure functions are written test-first.
- The slider rate passes the shared test cases.
- Components ship with their tests.

## Phase 1: Foundation

- [X] T001 [P] Test-first: `slackRate` in web/src/insights/slackRate.ts against every case in shared/test-cases/slack-feasibility.json, plus every published itinerary at its default setting (FR-002, SC-001, SC-002)
- [X] T002 [P] Test-first: `meterDots`, `monthBars` (with notes and the monthly minimum) and `findUrl` (FR-004, FR-006, FR-009)
- [X] T003 [P] Test-first: the `transfer` parameter in web/src/selection/ (parse, serialize, default omitted, invalid ignored; replace on change) (FR-003)

## Phase 2: US1, the transfer-time slider (P1)

- [X] T004 [US1] TransferSlider in the detail panel: a native range input from 15 to 120 minutes in steps of 5, the live rate text with its days and period, `aria-valuetext`, and the address parameter. Component and e2e tests: every itinerary at the default and at two other settings (FR-001 to FR-003)

## Phase 3: US2, risk visuals (P1)

- [X] T005 [US2] Meter, FailureBar and MonthChart, with component tests against the published data (FR-004 to FR-006)

## Phase 4: US3, insight panels (P2)

- [X] T006 [US3] Panels: faster alternatives (selectable), connecting options, buffer, why it didn't work, by month, about this itinerary; each with its definitions and plain "none" text. Component tests on every itinerary (FR-007, FR-008)

## Phase 5: US4, find and method (P3)

- [X] T007 [US4] The "Find this itinerary" link, and the MethodView at `?view=method` linked from the header (FR-009, FR-010)

## Phase 6: Polish

- [ ] T008 Visual references, axe and keyboard tests for the new controls; budgets; README, architecture and validation.md (FR-011, FR-012)
- [ ] T009 Independent review rounds until APPROVE; review.md
