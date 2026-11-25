# Contract: Command Line

The Phase 0 `flight-pipeline` command is extended. Exit codes are unchanged: 0 success, 1 validation or data-quality failure, 2 acquisition failure. Progress goes to stderr and a one-line summary to stdout.

| Command | Does | Writes |
|---|---|---|
| `acquire`, `prepare`, `select-hubs`, `build`, `analyze` | As in Phase 0, using `config/phase1.toml` and the new identity and layover rules | `data/derived/phase1/` |
| `curate` (new) | Selects showcase routes and the landing example (research R4) | `data/derived/phase1/showcase_routes.parquet` |
| `insights` (new) | Faster alternatives, connecting options, buffer, failure types, monthly view, schedule warnings, find parameters for the curated itineraries | `data/derived/phase1/insights.parquet` |
| `publish` (new) | Writes and validates the published JSON, checks the size budget, writes the showcase manifest | `site-data/showcase/` |
| `schemas` (new) | Writes the JSON Schema and regenerates the TypeScript types; `--check` compares with the committed files and exits 1 on any difference | `shared/schemas/`, `shared/types/` |
| `run` | Every stage in order, including `curate`, `insights` and `publish`; records runtime | all of the above |
| `verify` | Reruns every stage after `acquire` into a temporary directory (DB1B extraction included) and compares every output, including `site-data/showcase/` and the generated types, byte for byte | nothing outside the temporary directory |

`--config` defaults to `../config/phase1.toml` from `pipeline/`.
