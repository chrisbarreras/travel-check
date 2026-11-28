# Validation: Explorer Insights

Results on 2026-11-28 for the success criteria in [spec.md](spec.md).

| Criterion | Result |
|---|---|
| SC-001: slider default equals the published rate | Pass. A unit test runs `slackRate` on all 144 published itineraries at their own minimum connection time: the paired days, feasible days, status and rate equal the published `result`. The e2e test opens every itinerary at its default and at 15 and 90 minutes, and checks the shown text against the rule written out independently in the test |
| SC-002: shared test cases | Pass. `slackRate` passes every case in `shared/test-cases/slack-feasibility.json`, the same cases the pipeline passes |
| SC-003: visuals and panels equal the data | Pass. A component test opens all 144 itineraries and checks the meter's filled dots, the failure counts, the 12 monthly values (percent, "N d" below the monthly minimum, a dash with no flights), the number of faster alternatives and better connecting options, and the find link's address |
| SC-004: accessibility and keyboard | Pass. axe finds no violations (WCAG 2.2 AA) with a selected itinerary's slider and open panels at 360 and 1280 px, nor in the method view. The slider moves in 5-minute steps by keyboard, with `aria-valuetext` and a polite live result |
| SC-005: budgets | First-view scripts 95.1 KB gzip (limit 150); map scripts 279.4 KB gzip (limit 300). Lighthouse runs in CI (`web-lighthouse`) |
| Visual references | 9 references, including the selected itinerary with its panels at 360 and 1280 px and the method view at 360 px. The container suite (110 browser tests) passed in consecutive runs |

## Notes

- **No pipeline or contract change:** every figure shown is published by feature 002, or recomputed by the shared rule from its daily series.
- **Monthly rates:** a month's count of feasible days is its rate times its days. Rates are stored to 6 decimals, so this recovers the count exactly. It is rounded to a whole percent with the same rule as every other rate.
