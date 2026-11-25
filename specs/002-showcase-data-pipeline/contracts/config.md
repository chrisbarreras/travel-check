# Contract: Configuration (`config/phase1.toml`)

`config/phase1.toml` starts as a copy of `config/phase0.toml` (same pinned sources and checksums, July 2024 – June 2025) and adds the sections below. As before, every value is required and unknown keys are rejected. `config/phase0.toml` is left unchanged for the frozen Phase 0 results (research R15).

```toml
[itineraries]
# ... all Phase 0 keys, plus:
identity = "schedule"            # research R1; the only supported value in Phase 1
slot_window_min = 30             # departure-time window for a schedule slot
# median-layover pre-filter removed: layover limits apply through daily matching only (research R2)

[selection]
# ... Phase 0 keys; regional origin now means "outside the candidate pool" (FR-006)

[showcase]
routes_min = 8
routes_max = 12
itineraries_per_route_max = 12
max_share_route = 0.333          # of showcase comparisons
max_share_airline = 0.5
max_share_hub = 0.5
regional_share_min = 0.5         # of selected routes, when enough exist
cross_hub_share_min = 0.5        # of showcase comparisons (SC-002, research R4 step 5)
size_budget_kb = 2048            # gzip-compressed published files
landing_budget_kb = 150          # gzip-compressed landing.json; the load-time proxy for SC-007
output_dir = "site-data/showcase"

[insights]
faster_min_saving_min = 15
faster_margin = 0.02             # lower bound of the paired 95% CI no worse than -2 points
faster_departure_window_min = 180
buffer_share = 0.95
buffer_round_min = 5
monthly_min_sample = 20
schedule_change_min_shift_min = 10
schedule_change_min_days = 7

[notes]
disruption_file = "config/disruption_notes.toml"
```

## `config/disruption_notes.toml`

```toml
[[note]]
id = "crowdstrike-2024-07"
start = "2024-07-19"
end = "2024-07-24"
airlines = ["DL"]
airports = []
text = "Global IT outage (CrowdStrike update); Delta cancelled thousands of flights over several days."
source = "https://www.transportation.gov/..."   # a public source is required; entries without one are rejected
```

## Validation rules

- All Phase 0 rules hold.
- `routes_min` ≤ `routes_max`; shares in (0, 1]; `faster_margin` in [0, 0.2]; `buffer_share` in (0.5, 1).
- `slot_window_min` in 10–90.
- Every disruption note has an id, a date range inside the period, at least one airline or airport, a text and an `https` source.
