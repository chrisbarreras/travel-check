# Flight App

A map-first explorer that compares how reliable flight itineraries are, using real historical on-time data: not only how long a trip takes, but how often its connection would actually have worked.

**Status: Phase 0, the data feasibility experiment, is complete; the decision is GO.** Before building any interface, the project checked whether public flight data shows meaningful differences in connection feasibility between itineraries a traveler would otherwise consider equivalent. It does: 81 showcase examples in 9 origin/destination pairs across 5 hubs, from July 2024 to June 2025 (decision in [ADR-0012](docs/adr/0012-phase0-go-no-go.md); full report in [reports/phase0/summary.md](reports/phase0/summary.md)). The Phase 0 results are frozen at the git tag `phase0-final`. Next is Phase 1 in the [roadmap](docs/roadmap.md).

## Run the Phase 0 pipeline

Requires [uv](https://docs.astral.sh/uv/) (it installs Python 3.13) and about 6 GB of disk space (each DB1B quarter is extracted to about 2 GB while it is processed, then deleted).

```bash
cd pipeline
uv sync
uv run pytest                                            # unit and end-to-end tests, no network
uv run flight-pipeline run --config ../config/phase0.toml   # download, analyze, report
uv run flight-pipeline verify --config ../config/phase0.toml  # rerun and compare with the committed results
```

Every input is pinned by checksum in [config/phase0.toml](config/phase0.toml), so `run` reproduces the committed numbers exactly. Details: [quickstart](specs/001-bts-connection-experiment/quickstart.md). The analysis notebook (`uv run marimo edit ../notebooks/phase0_connection_experiment.py`) only reads the pipeline's outputs.

## Repository map

| Path | Contents |
|---|---|
| [docs/roadmap.md](docs/roadmap.md) | Phases 0–5 and their features |
| [docs/methodology.md](docs/methodology.md) | How every number is defined and computed |
| [docs/design.md](docs/design.md) | Visual and interaction direction for the explorer |
| [docs/adr/](docs/adr/README.md) | Architecture decision records |
| [specs/](specs/) | Spec Kit feature specifications, plans, tasks and reviews |
| [pipeline/](pipeline/) | Python data pipeline (`flight_pipeline`) and its tests |
| [reports/phase0/](reports/phase0/) | Committed Phase 0 results, data-quality counts and run manifest |
| [notebooks/](notebooks/) | marimo analysis notebook |

The project follows spec-driven development with [GitHub Spec Kit](https://github.com/github/spec-kit) under the rules in [.specify/memory/constitution.md](.specify/memory/constitution.md).

## Data and attribution

- Flight data: U.S. Department of Transportation, Bureau of Transportation Statistics (TranStats): Marketing Carrier On-Time Performance, T-100 Domestic Segment (U.S. Carriers) and the Airline Origin and Destination Survey (DB1B Market).
- Airport time zones: [airportsdata](https://github.com/mborsetti/airportsdata), MIT License, Copyright (c) 2020- Mike Borsetti (includes data Copyright (c) 2014 mwgg).
- Time-zone rules: tzdata, Apache License 2.0.

Results describe **connection feasibility** from historical schedules and actual gate times. They are not predictions, and they do not describe what happened to any traveler.
