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
