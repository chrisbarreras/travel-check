# Contract: Configuration File

`config/phase0.toml`, validated by Pydantic models in `flight_pipeline.config`. Every value below is required in the file (no hidden defaults); the values shown are the spec defaults.

```toml
seed = 20261124

[paths]
# Relative paths resolve against the repository root (the parent of the config file's directory)
raw_dir = "data/raw"
derived_dir = "data/derived/phase0"
reports_dir = "reports/phase0"

[period]                          # one period for all sources (amendment 1); whole quarters
start = "2024-07"                 # inclusive, YYYY-MM
end   = "2025-06"

[sources.ontime]
url_pattern = "https://www.transtats.bts.gov/PREZIP/On_Time_Marketing_Carrier_On_Time_Performance_Beginning_January_2018_{year}_{month}.zip"
overrides = {}                    # "YYYY-MM" = "full URL" for irregular file names

[sources.ontime.checksums]         # "YYYY-MM" = sha256 of the monthly zip, pinned after first download

[sources.db1b]
url_pattern = "https://www.transtats.bts.gov/PREZIP/Origin_and_Destination_Survey_DB1BMarket_{year}_{quarter}.zip"

[sources.db1b.checksums]          # "YYYY-Q" = sha256 of the quarterly zip, pinned after first download

[sources.t100]
manual_file = "data/raw/t100/t100_segment.csv"   # used when scripted download fails
checksum = ""                     # sha256 of the combined CSV; pin after the first download

[timezones]
overrides = {}                    # "IATA" = { tz = "America/...", source = "..." }

[hubs]
candidate_pool_size = 30
airline_share_min = 0.05
eligible_itineraries_min = 15
weights = { airlines = 1.0, departures = 1.0, passengers = 1.0 }
count = 7                         # allowed 5–8
major_networks = ["AA", "DL", "UA", "WN", "AS"]
winter_months = [12, 1, 2]
spring_months = [3, 4, 5]
summer_months = [6, 7, 8]
autumn_months = [9, 10, 11]
min_winter_peak = 2
min_summer_peak = 2

[itineraries]
min_connection_default_min = 30
min_connection_partner_min = 45
min_connection_by_hub = {}        # "IATA" = minutes
max_layover_min = 240
recurrence_threshold = 0.60     # connection-level: share of days the two flights connect
partners = [["AA", "AS"]]
min_sold_passengers = 30          # sampled DB1B passengers on the routing over the period
carrier_map = {}                  # DB1B selling-airline code -> on-time marketing code

[feasibility]
boarding_cutoff_min = 15
min_sample_days = 30

[selection]
od_pairs_count = 15               # allowed 10–15
regional_share_min = 0.5
max_pairs_per_hub = 3

[comparison]
travel_time_tolerance_min = 60
departure_window_min = 180
showcase_gap = 0.10
ci_level = 0.95
bootstrap_resamples = 10000
go_min_examples = 3
go_min_hubs = 2

[sensitivity]
min_connection_min = [20, 30, 45]
boarding_cutoff_min = [10, 15, 20]
recurrence_threshold = [0.50, 0.60, 0.75]

[quality]
clock_mismatch_max_share = 0.01   # fail the run above this share

[runtime]
limit_min = 30                    # SC-008; `run` warns and records `runtime_exceeded` above this
```

## Validation rules

- `hubs.count` in 5–8; `selection.od_pairs_count` in 10–15; shares and thresholds in 0–1.
- The default values of `itineraries` and `feasibility` must appear in the corresponding `sensitivity` lists.
- The period is exactly 12 months and starts and ends on quarter boundaries (start month 1, 4, 7 or 10).
- The four season month lists together contain each month 1–12 exactly once.
- Unknown keys are rejected.
