# Validation: Web Foundation

Results of the [quickstart](quickstart.md) scenarios (T035, T042).

## Merge ruleset on `main`

Created with `gh api -X POST repos/chrisbarreras/travel-check/rulesets --input ruleset.json` (ruleset 28267343), and Pages enabled with `gh api -X POST repos/chrisbarreras/travel-check/pages -f build_type=workflow`, on 2026-11-27 with the owner's authorization.

```json
{
  "name": "main: pull requests and required checks",
  "target": "branch",
  "enforcement": "active",
  "conditions": { "ref_name": { "include": ["~DEFAULT_BRANCH"], "exclude": [] } },
  "rules": [
    { "type": "deletion" },
    { "type": "non_fast_forward" },
    {
      "type": "pull_request",
      "parameters": {
        "required_approving_review_count": 0,
        "dismiss_stale_reviews_on_push": false,
        "require_code_owner_review": false,
        "require_last_push_approval": false,
        "required_review_thread_resolution": false
      }
    },
    {
      "type": "required_status_checks",
      "parameters": {
        "strict_required_status_checks_policy": false,
        "required_status_checks": [
          { "context": "checks", "integration_id": 15368 },
          { "context": "web-checks", "integration_id": 15368 },
          { "context": "web-browser", "integration_id": 15368 },
          { "context": "web-lighthouse", "integration_id": 15368 }
        ]
      }
    }
  ]
}
```

## Breakage tests (SC-005, quickstart 11)

One draft pull request per kind of breakage, each branched from this feature and targeting `main`, then closed unmerged on 2026-11-27. "Blocked" is GitHub's merge state (`BLOCKED`) with the named required check failing.

| PR | Breakage | Failing required check (step or Playwright project) | Merge |
|---|---|---|---|
| #2 | Unused variable in `App.tsx` | `web-checks` (Lint) | Blocked |
| #3 | String assigned to a `number` | `web-checks` (Types) | Blocked |
| #4 | `percentOf` rounds down instead of half away from zero | `web-checks` (Unit and component tests); `web-browser` (visual: 64% became 63%) | Blocked |
| #5 | "Worked more often" badge removed | `web-checks` (Unit and component tests); `web-browser` (visual) | Blocked |
| #6 | Cards forced to 420 px wide | `web-browser` (e2e: horizontal scroll at 320 and 360 px; visual) | Blocked |
| #7 | Accent color changed by one step (`#1c56c2` → `#1c56c4`) | `web-browser` (visual) | Blocked |
| #8 | Muted text at low contrast | `web-browser` (a11y; visual); `web-lighthouse` (accessibility below 1.00) | Blocked |
| #9 | Focus outline removed from the definitions | `web-browser` (keyboard) | Blocked |
| #10 | 160 KB of incompressible ballast in the bundle | `web-checks` (Size budgets: 247 KB against 150 KB) | Blocked |

The clean pull request is this feature's own (#1): every required check passes.

**Two fixes came out of the first round:**
- **The visual check missed #7.** Playwright's default per-pixel color tolerance (0.2) absorbed the one-step color change. Screenshots are compared only in the pinned container, so the comparison is now exact (`threshold: 0`).
- **Two breakages didn't reach their target.** #5 and #10 first failed at Format, before their target check could run. They were reformatted and rerun, so each breakage reaches its target. #10 also needed its ballast used, not just measured, or the minifier dropped it.

## Scenarios

Run on 2026-11-27. Local results are from Windows 11 with Docker Desktop. CI results are from GitHub-hosted `ubuntu-latest` runners.

| # | Scenario | Result |
|---|---|---|
| 1 | Static checks | Pass: Prettier, ESLint (no warnings), `tsc` strict |
| 2 | Unit and component tests | Pass: 95 tests, offline, including the display rules and the malformed-data cases |
| 3 | Build copies data unchanged (FR-016) | Pass: `check-data-copy` finds the 15 files byte-identical |
| 4 | Budgets (SC-002) | Pass: scripts 85.0 KB gzip (budget 150 KB); first-view data 8.8 KB gzip (index 3.3, landing 3.7, manifest 1.8; budget 150 KB) |
| 5 | Landing figures exact (US1, SC-003) | Pass: Delta via ATL worked on 92% of 298 days; United via ORD on 64% of 291 days; +28 points, 95% interval +22 to +35, over 242 days both flew; Jul 2024 – Jun 2025. Asserted against the data files at 4 widths |
| 6 | Phone layout (SC-009) | Pass: no horizontal scroll at 320, 360, 768 and 1280 px, or at 200% text size; standalone targets at least 44 px |
| 7 | Accessibility and keyboard (SC-004) | Pass: no axe violations (WCAG 2.2 AA) at 360 and 1280 px and in the error state; all 10 controls reached by Tab and Shift+Tab in order, each with a 3 px outline |
| 8 | Visual references | Pass: 4 references (landing at 360 and 1280 px, the error and loading states at 360 px) match exactly |
| 9 | Honest failures (US3) | Pass: malformed, missing and unreachable data show "This example could not be loaded" with no figures; loading shows the layout's shape without digits |
| 10 | Lighthouse (SC-001) | Pass: median performance 100, accessibility 100, LCP 0.75 s, CLS 0 (locally); `web-lighthouse` passes in CI |
| 11 | Breakages block merges (SC-005) | Pass: see Breakage tests above |
| 13 | CI time (SC-007) | Pass: `web-checks` about 25 s, `web-browser` 50–56 s, `web-lighthouse` about 70 s; each web job is about a minute, against a 15-minute limit |
| 14 | Reproducible screenshots (SC-006) | Pass: `web-browser` ran 3 times on commit adb7eff (run 46079716719, attempts 1–3), all passing. The CI screenshots matched the references made locally in the same pinned image |
| 12 | Deployment and smoke check (SC-008) | After merge: recorded below |
