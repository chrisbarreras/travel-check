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
