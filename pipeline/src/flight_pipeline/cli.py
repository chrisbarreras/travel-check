"""Command-line stages (contracts/cli.md).

Exit codes: 0 success; 1 validation or data-quality failure; 2 acquisition failure.
Progress goes to stderr; a one-line result summary goes to stdout.
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
import time
from collections.abc import Callable, Sequence
from dataclasses import asdict
from pathlib import Path

import httpx
from pydantic import ValidationError

from flight_pipeline import __version__, schemas
from flight_pipeline.config import Config, ConfigError, load_config
from flight_pipeline.models import (
    FlightRecord,
    PassengerTraffic,
    QualitySummary,
    SoldRouting,
    SoldRoutingsSummary,
    SourceRecord,
)
from flight_pipeline.prepare.db1b import prepare_sold_routings
from flight_pipeline.prepare.normalize import HeaderError, normalize_ontime
from flight_pipeline.prepare.quality import QualityError, QualityReport
from flight_pipeline.providers.base import AcquisitionError, SourceFile
from flight_pipeline.providers.bts_db1b import BtsDb1bProvider, quarter_key
from flight_pipeline.providers.bts_ontime import BtsOnTimeProvider, month_key
from flight_pipeline.providers.bts_t100 import BtsT100Provider, load_passengers
from flight_pipeline.providers.timezones import AirportsDataTimezones, MissingTimezoneError
from flight_pipeline.showcase.publish import PublishError
from flight_pipeline.stages import (
    SHOWCASE_MANIFEST,
    stage_analyze,
    stage_build,
    stage_curate,
    stage_insights,
    stage_publish,
    stage_report,
    stage_select_hubs,
    write_showcase_manifest,
)
from flight_pipeline.storage import connect, write_table

USER_AGENT = f"flight-pipeline/{__version__}"


class StageError(RuntimeError):
    """A stage cannot run (for example, its inputs are missing). Exit code 1."""


def progress(message: str) -> None:
    print(message, file=sys.stderr, flush=True)


def _months(cfg: Config, selected: Sequence[str] | None) -> list[tuple[int, int]]:
    period = cfg.period.months()
    if not selected:
        return period
    keys = {month_key(y, m): (y, m) for y, m in period}
    unknown = [m for m in selected if m not in keys]
    if unknown:
        raise StageError(
            f"--month {', '.join(unknown)} is outside the period "
            f"{cfg.period.start} to {cfg.period.end}"
        )
    return [keys[m] for m in sorted(set(selected))]


def _write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def cmd_acquire(cfg: Config, months: list[tuple[int, int]], client: httpx.Client) -> str:
    raw = cfg.path(cfg.paths.raw_dir)
    progress(f"acquire: on-time data for {len(months)} month(s)")
    files: list[SourceFile] = BtsOnTimeProvider(cfg.sources.ontime, raw, client).acquire(months)
    quarters = cfg.period.quarters()
    progress(f"acquire: DB1B Market data for {len(quarters)} quarter(s)")
    files += BtsDb1bProvider(cfg.sources.db1b, raw, client).acquire(quarters)
    progress("acquire: T-100 passenger data")
    t100 = BtsT100Provider(
        cfg.sources.t100,
        cfg.path(cfg.sources.t100.manual_file),
        cfg.period.months(),
        client,
    ).acquire()
    files.append(t100)
    record = [{**asdict(f), "path": str(f.path)} for f in files]
    for r in record:
        SourceRecord.model_validate(r)
    _write_json(raw / "sources.json", record)
    unpinned = [f.name for f in files if not f.pinned]
    for f in files:
        if not f.pinned:
            progress(f"  not pinned: {f.name} sha256={f.sha256}")
    note = f"; {len(unpinned)} unpinned" if unpinned else ""
    return f"acquired {len(files)} source file(s){note}"


def cmd_prepare(cfg: Config, months: list[tuple[int, int]]) -> str:
    raw = cfg.path(cfg.paths.raw_dir)
    derived = cfg.path(cfg.paths.derived_dir)
    reports = cfg.path(cfg.paths.reports_dir)
    csvs = [raw / "ontime" / f"{month_key(y, m)}.csv" for y, m in months]
    missing = [str(p) for p in csvs if not p.exists()]
    if missing:
        raise StageError(f"raw on-time file(s) missing: {', '.join(missing)}; run `acquire` first")
    t100_csv = cfg.path(cfg.sources.t100.manual_file)
    if not t100_csv.exists():
        raise StageError(f"T-100 file missing: {t100_csv}; run `acquire` first")
    db1b = [
        (quarter_key(y, q), raw / "db1b" / f"{quarter_key(y, q)}.zip")
        for y, q in cfg.period.quarters()
    ]
    missing = [str(p) for _, p in db1b if not p.exists()]
    if missing:
        raise StageError(f"raw DB1B file(s) missing: {', '.join(missing)}; run `acquire` first")

    con = connect()
    progress(f"prepare: normalizing {len(csvs)} on-time file(s)")
    report: QualityReport
    try:
        report = normalize_ontime(
            con,
            csvs,
            AirportsDataTimezones(cfg.timezones.overrides),
            clock_mismatch_max_share=cfg.quality.clock_mismatch_max_share,
        )
    except QualityError as exc:
        _write_json(
            reports / "quality.json",
            QualitySummary.model_validate(exc.report.to_json()).model_dump(),
        )
        raise
    _write_json(
        reports / "quality.json", QualitySummary.model_validate(report.to_json()).model_dump()
    )
    progress("prepare: validating and writing flights.parquet")
    n_flights = write_table(
        con,
        "flights",
        derived / "flights.parquet",
        FlightRecord,
        list(FlightRecord.model_fields),  # total order, even for conflicting copies
    )
    progress("prepare: passenger data")
    load_passengers(con, t100_csv, cfg.period.months(), "passengers")
    n_pax = write_table(
        con,
        "passengers",
        derived / "passengers.parquet",
        PassengerTraffic,
        ["year", "month", "origin", "carrier"],
    )
    progress(f"prepare: sold routings from {len(db1b)} DB1B quarter(s)")
    db1b_report = prepare_sold_routings(
        con, db1b, cfg.itineraries.carrier_map, derived / "db1b_extract", "sold_routings"
    )
    n_sold = write_table(
        con,
        "sold_routings",
        derived / "sold_routings.parquet",
        SoldRouting,
        ["origin", "hub", "dest", "airline_in", "airline_out"],
    )
    _write_json(
        derived / "sold_routings.json",
        SoldRoutingsSummary.model_validate(db1b_report.to_json()).model_dump(),
    )
    totals = report.totals()
    excluded = sum(
        totals.get(k, 0)
        for k in (
            "duplicate",
            "conflicting_duplicate",
            "missing_actual_times",
            "clock_time_mismatch",
        )
    )
    return (
        f"prepared {n_flights} flights ({excluded} flagged), {n_pax} passenger rows, "
        f"{n_sold} sold routings ({db1b_report.unknown_airline_share:.2%} of DB1B passengers "
        f"with an unknown selling airline); clock mismatch {report.clock_mismatch_share:.4%}"
    )


def cmd_run(cfg: Config, config_path: Path, client: httpx.Client | None, *, acquire: bool) -> str:
    """All stages in order. Runtime excludes downloads and is recorded in the manifest."""
    if acquire:
        progress(cmd_acquire(cfg, cfg.period.months(), _client(client)))
    started = time.perf_counter()
    progress(cmd_prepare(cfg, cfg.period.months()))
    for name, stage in (
        ("select-hubs", stage_select_hubs),
        ("build", stage_build),
        ("analyze", stage_analyze),
        ("curate", stage_curate),
        ("insights", stage_insights),
    ):
        progress(f"{name}: {stage(connect(), cfg)}")
    progress(f"publish: {stage_publish(connect(), cfg, config_path)}")
    runtime_min = (time.perf_counter() - started) / 60
    summary = stage_report(connect(), cfg, config_path, runtime_min)
    write_showcase_manifest(cfg, config_path, runtime_min)
    if runtime_min > cfg.runtime.limit_min:
        progress(
            f"warning: runtime {runtime_min:.1f} min exceeds the {cfg.runtime.limit_min} min "
            "limit (SC-008)"
        )
    return f"{summary}; runtime {runtime_min:.1f} min excluding downloads"


MANIFEST_IDENTITY = ("config_sha256", "notes_sha256", "sources", "packages")


def _tree(root: Path) -> dict[str, bytes]:
    return (
        {p.relative_to(root).as_posix(): p.read_bytes() for p in sorted(root.rglob("*.json"))}
        if root.exists()
        else {}
    )


def compare_showcase(committed: Path, fresh: Path) -> list[str]:
    """Every published file byte for byte (the manifest by its input identities)."""
    old, new = _tree(committed), _tree(fresh)
    out: list[str] = []
    for name in sorted(set(old) | set(new)):
        if name == SHOWCASE_MANIFEST:
            continue
        if name not in old:
            out.append(f"showcase/{name}: missing from the committed files")
        elif name not in new:
            out.append(f"showcase/{name}: not produced by the rerun")
        elif old[name] != new[name]:
            out.append(f"showcase/{name}: committed file differs from the rerun")
    if SHOWCASE_MANIFEST not in old:
        out.append(f"showcase/{SHOWCASE_MANIFEST}: missing from the committed files")
    elif SHOWCASE_MANIFEST in new:
        a, b = json.loads(old[SHOWCASE_MANIFEST]), json.loads(new[SHOWCASE_MANIFEST])
        out += [f"showcase manifest {k} differs" for k in MANIFEST_IDENTITY if a.get(k) != b.get(k)]
    return out


def cmd_verify(cfg: Config, config_path: Path) -> str:
    """SC-001, specs/002 FR-025: rerun every stage after acquire into a temporary directory
    (DB1B extraction included) and compare every output with the committed files: the Phase 0
    reports and output hashes, every published showcase file byte for byte, the showcase
    manifest's inputs, and the generated schema and types. Each difference is named."""
    committed_manifest = cfg.path(cfg.paths.reports_dir) / "manifest.json"
    if not committed_manifest.exists():
        raise StageError(f"{committed_manifest} not found; run `run` first")
    committed = json.loads(committed_manifest.read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory(prefix="flight-verify-") as tmp:
        paths = cfg.paths.model_copy(
            update={
                "raw_dir": str(cfg.path(cfg.paths.raw_dir)),
                "derived_dir": str(Path(tmp) / "derived"),
                "reports_dir": str(Path(tmp) / "reports"),
            }
        )
        showcase = cfg.showcase.model_copy(update={"output_dir": str(Path(tmp) / "showcase")})
        rerun_cfg = cfg.model_copy(update={"paths": paths, "showcase": showcase})
        progress("verify: rerunning all stages after acquire")
        progress(cmd_prepare(rerun_cfg, rerun_cfg.period.months()))
        for stage in (stage_select_hubs, stage_build, stage_analyze, stage_curate, stage_insights):
            progress(stage(connect(), rerun_cfg))
        progress(stage_publish(connect(), rerun_cfg, config_path))
        stage_report(connect(), rerun_cfg, config_path, None)
        fresh = json.loads((Path(tmp) / "reports" / "manifest.json").read_text(encoding="utf-8"))
        committed_dir = cfg.path(cfg.paths.reports_dir)
        differences = [
            f"{name}: committed file differs from the rerun"
            for name in ("summary.json", "summary.md", "quality.json")
            if not (committed_dir / name).exists()
            or (committed_dir / name).read_bytes() != (Path(tmp) / "reports" / name).read_bytes()
        ]
        differences += compare_showcase(cfg.path(cfg.showcase.output_dir), Path(tmp) / "showcase")
    for key in ("config_sha256", "sources", "packages"):
        if committed.get(key) != fresh.get(key):
            differences.append(f"{key} differs")
    old, new = committed.get("outputs", {}), fresh.get("outputs", {})
    for name in sorted(set(old) | set(new)):
        if old.get(name) != new.get(name):
            differences.append(f"{name}: {old.get(name)} != {new.get(name)}")
    differences += schemas.differences(cfg.repo_root, schemas.generate(schemas.npx_generator))
    if differences:
        raise StageError("not reproducible:\n  " + "\n  ".join(differences))
    return (
        f"identical: {len(new)} outputs, the published showcase and the generated types match "
        "the committed files"
    )


def cmd_schemas(cfg: Config, *, check: bool) -> str:
    """Write, or with ``check`` compare, the JSON Schema and generated TypeScript types
    (specs/002 research R6). A difference under ``check`` exits 1."""
    files = schemas.generate(schemas.npx_generator)
    if check:
        diffs = schemas.differences(cfg.repo_root, files)
        if diffs:
            raise StageError(
                "; ".join(diffs) + "; run `flight-pipeline schemas` and commit the result"
            )
        return f"schemas up to date: {', '.join(sorted(files))}"
    schemas.write(cfg.repo_root, files)
    return f"wrote {', '.join(sorted(files))}"


def _client(client: httpx.Client | None) -> httpx.Client:
    return client or httpx.Client(headers={"User-Agent": USER_AGENT})


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="flight-pipeline", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    commands = (
        ("acquire", "download on-time, DB1B and T-100 source files", True),
        (
            "prepare",
            "normalize flights to UTC, run quality checks, load passenger data and sold routings",
            True,
        ),
        ("select-hubs", "compute candidate metrics and select hubs", False),
        ("build", "build itineraries and select origin/destination pairs", False),
        ("analyze", "daily outcomes, all scenarios, comparable pairs, showcases", False),
        ("curate", "select showcase routes, balanced comparisons and the landing example", False),
        (
            "insights",
            "faster alternatives, connecting options, buffer, monthly view and more",
            False,
        ),
        ("publish", "write the validated showcase JSON within the size budgets", False),
        ("schemas", "write the JSON Schema and generated TypeScript types", False),
        ("report", "write summary.json, summary.md and manifest.json", False),
        ("run", "run every stage in order", False),
        ("verify", "rerun and compare with the committed reports (SC-001)", False),
    )
    for name, help_text, monthly in commands:
        p = sub.add_parser(name, help=help_text)
        p.add_argument("--config", type=Path, default=Path("../config/phase1.toml"))
        if monthly:
            p.add_argument(
                "--month",
                action="append",
                metavar="YYYY-MM",
                help="limit on-time data to these months (repeatable; default: whole period)",
            )
        if name == "schemas":
            p.add_argument(
                "--check",
                action="store_true",
                help="compare with the committed files and exit 1 on any difference",
            )
        if name == "run":
            p.add_argument(
                "--no-acquire",
                action="store_true",
                help="use raw files already in place instead of acquiring them",
            )
    return parser


def main(argv: Sequence[str] | None = None, *, client: httpx.Client | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        cfg = load_config(args.config)
        months = _months(cfg, getattr(args, "month", None))
        commands: dict[str, Callable[[], str]] = {
            "acquire": lambda: cmd_acquire(cfg, months, _client(client)),
            "prepare": lambda: cmd_prepare(cfg, months),
            "select-hubs": lambda: stage_select_hubs(connect(), cfg),
            "build": lambda: stage_build(connect(), cfg),
            "analyze": lambda: stage_analyze(connect(), cfg),
            "curate": lambda: stage_curate(connect(), cfg),
            "insights": lambda: stage_insights(connect(), cfg),
            "publish": lambda: stage_publish(connect(), cfg, args.config),
            "schemas": lambda: cmd_schemas(cfg, check=args.check),
            "report": lambda: stage_report(connect(), cfg, args.config),
            "run": lambda: cmd_run(cfg, args.config, client, acquire=not args.no_acquire),
            "verify": lambda: cmd_verify(cfg, args.config),
        }
        summary = commands[args.command]()
    except AcquisitionError as exc:
        progress(f"error: {exc}")
        return 2
    except (
        ConfigError,
        StageError,
        PublishError,
        schemas.SchemaError,
        HeaderError,
        MissingTimezoneError,
        QualityError,
        ValidationError,
        ValueError,
        FileNotFoundError,
    ) as exc:
        progress(f"error: {exc}")
        return 1
    print(summary, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
