"""Command-line interface: acquire and prepare (contracts/cli.md)."""

import json
import shutil
import zipfile
from pathlib import Path

import duckdb
import httpx
import pytest

from flight_pipeline.cli import main
from tests.unit.test_db1b import quarter_zips

REPO = Path(__file__).resolve().parents[3]
FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def make_config(tmp_path: Path, **replacements: str) -> Path:
    text = (REPO / "config" / "phase1.toml").read_text()
    text = text.replace('raw_dir = "data/raw"', f'raw_dir = "{(tmp_path / "raw").as_posix()}"')
    text = text.replace(
        'derived_dir = "data/derived/phase1"',
        f'derived_dir = "{(tmp_path / "derived").as_posix()}"',
    )
    text = text.replace(
        'reports_dir = "reports/phase1"', f'reports_dir = "{(tmp_path / "reports").as_posix()}"'
    )
    text = text.replace(
        'manual_file = "data/raw/t100/t100_segment.csv"',
        f'manual_file = "{(tmp_path / "raw" / "t100" / "t100_segment.csv").as_posix()}"',
    )
    text = text.replace(
        'url_pattern = "https://www.transtats.bts.gov/PREZIP/On_Time_Marketing_Carrier_On_Time_Performance_Beginning_January_2018_{year}_{month}.zip"',
        'url_pattern = "https://example.test/{year}_{month}.zip"',
    )
    # The fixtures are from 2025-12 to 2026-01: a quarter-aligned period that contains them.
    text = text.replace('start = "2024-07"', 'start = "2025-10"')
    text = text.replace('end   = "2025-06"', 'end   = "2026-09"')
    for old, new in replacements.items():
        text = text.replace(old, new)
    path = tmp_path / "config" / "phase1.toml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


def stage_raw(tmp_path: Path) -> None:
    ontime = tmp_path / "raw" / "ontime"
    ontime.mkdir(parents=True)
    shutil.copy(FIXTURES / "ontime_sample.csv", ontime / "2026-01.csv")
    t100 = tmp_path / "raw" / "t100"
    t100.mkdir(parents=True)
    shutil.copy(FIXTURES / "t100_sample.csv", t100 / "t100_segment.csv")
    zips = dict(quarter_zips(tmp_path / "raw"))
    header = (FIXTURES / "db1b_sample.csv").read_text(encoding="utf-8").splitlines()[0]
    for key in ("2026-2", "2026-3"):  # quarters with no fixture rows
        with zipfile.ZipFile(tmp_path / "raw" / "db1b" / f"{key}.zip", "w") as zf:
            zf.writestr(f"Market_{key}.csv", header + "\n")
    assert sorted(zips) == ["2025-4", "2026-1"]


def test_prepare_writes_outputs_and_summary(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    stage_raw(tmp_path)
    code = main(
        [
            "prepare",
            "--config",
            str(
                make_config(
                    tmp_path,
                    **{"clock_mismatch_max_share = 0.01": "clock_mismatch_max_share = 0.2"},
                )
            ),
            "--month",
            "2026-01",
        ]
    )
    out, err = capsys.readouterr()
    assert code == 0, err
    assert len(out.strip().splitlines()) == 1
    assert "222 flights" in out
    assert "8 sold routings" in out
    assert (tmp_path / "derived" / "flights.parquet").exists()
    assert (tmp_path / "derived" / "sold_routings.parquet").exists()
    assert not list((tmp_path / "raw" / "db1b" / "extract").glob("*.csv"))
    sold = json.loads((tmp_path / "derived" / "sold_routings.json").read_text())
    assert sold["quarters"] == ["2025-4", "2026-1"]
    assert (tmp_path / "derived" / "passengers.parquet").exists()
    quality = json.loads((tmp_path / "reports" / "quality.json").read_text())
    assert quality["totals"]["duplicate"] == 1
    con = duckdb.connect()
    pax = (tmp_path / "derived" / "passengers.parquet").as_posix()
    n = con.execute(f"SELECT count(*) FROM read_parquet('{pax}')").fetchone()
    assert n == (7,)  # rows inside the T-100 period, summed by airport/carrier/month


def test_prepare_quality_failure_exits_1(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    stage_raw(tmp_path)
    # 1 mismatch among ~120 checked flights is above a 0.1% limit
    cfg = make_config(
        tmp_path, **{"clock_mismatch_max_share = 0.01": "clock_mismatch_max_share = 0.001"}
    )
    code = main(["prepare", "--config", str(cfg), "--month", "2026-01"])
    _, err = capsys.readouterr()
    assert code == 1
    assert "clock-time mismatch" in err
    assert (tmp_path / "reports" / "quality.json").exists()  # written even on failure


def test_prepare_without_raw_data_exits_1(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code = main(["prepare", "--config", str(make_config(tmp_path)), "--month", "2026-01"])
    _, err = capsys.readouterr()
    assert code == 1
    assert "acquire" in err


def test_bad_config_exits_1(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    code = main(["prepare", "--config", str(make_config(tmp_path, **{"count = 7": "count = 9"}))])
    _, err = capsys.readouterr()
    assert code == 1
    assert "hubs.count" in err


def test_acquire_failure_exits_2(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    client = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(404)))
    code = main(
        ["acquire", "--config", str(make_config(tmp_path)), "--month", "2026-01"], client=client
    )
    _, err = capsys.readouterr()
    assert code == 2
    assert "example.test/2026_1.zip" in err


def test_month_outside_period_rejected(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    code = main(["prepare", "--config", str(make_config(tmp_path)), "--month", "2024-01"])
    _, err = capsys.readouterr()
    assert code == 1
    assert "2024-01" in err
