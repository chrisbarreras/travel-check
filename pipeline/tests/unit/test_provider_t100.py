"""T-100 segment passenger data: scripted form download with manual fallback (research R2)."""

import hashlib
import io
import zipfile
from pathlib import Path
from urllib.parse import parse_qs

import httpx
import pytest

from flight_pipeline.config import T100SourceConfig
from flight_pipeline.providers.base import AcquisitionError, ChecksumError
from flight_pipeline.providers.bts_t100 import FORM_URL, BtsT100Provider

FORM_HTML = """<html><form method="post">
<input type="hidden" name="__VIEWSTATE" id="__VIEWSTATE" value="vs123" />
<input type="hidden" name="__VIEWSTATEGENERATOR" id="__VIEWSTATEGENERATOR" value="gen1" />
<input type="hidden" name="__EVENTVALIDATION" id="__EVENTVALIDATION" value="ev9" />
</form></html>"""


def month_zip(year: int, month: int) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("Documentation.csv", "doc")
        zf.writestr(
            "T_T100D_SEGMENT_US_CARRIER_ONLY.csv",
            "PASSENGERS,UNIQUE_CARRIER,ORIGIN,YEAR,MONTH\n"
            f"100.00,AA,ORD,{year},{month}\n"
            f"50.00,UA,ORD,{year},{month}\n",
        )
    return buf.getvalue()


class FormServer:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.posts: list[dict[str, list[str]]] = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        if request.method == "GET":
            return httpx.Response(200, text=FORM_HTML)
        form = parse_qs(request.content.decode())
        self.posts.append(form)
        if self.fail:
            return httpx.Response(
                200, text="<html>error</html>", headers={"content-type": "text/html"}
            )
        year, month = int(form["cboYear"][0]), int(form["cboPeriod"][0])
        return httpx.Response(
            200, content=month_zip(year, month), headers={"content-type": "application/zip"}
        )

    def client(self) -> httpx.Client:
        return httpx.Client(transport=httpx.MockTransport(self.handler))


MONTHS = [(2025, 12), (2026, 1)]


def provider(tmp_path: Path, server: FormServer, checksum: str = "") -> BtsT100Provider:
    cfg = T100SourceConfig(manual_file="data/raw/t100/t100_segment.csv", checksum=checksum)
    return BtsT100Provider(cfg, tmp_path / cfg.manual_file, MONTHS, server.client())


def test_scripted_download_combines_months(tmp_path: Path) -> None:
    server = FormServer()
    f = provider(tmp_path, server).acquire()
    lines = f.path.read_text().splitlines()
    assert lines[0] == "PASSENGERS,UNIQUE_CARRIER,ORIGIN,YEAR,MONTH"
    assert lines[1:] == [
        "100.00,AA,ORD,2025,12",
        "50.00,UA,ORD,2025,12",
        "100.00,AA,ORD,2026,1",
        "50.00,UA,ORD,2026,1",
    ]
    assert f.sha256 == hashlib.sha256(f.path.read_bytes()).hexdigest()
    assert f.url == FORM_URL


def test_scripted_post_sends_form_state_and_fields(tmp_path: Path) -> None:
    server = FormServer()
    provider(tmp_path, server).acquire()
    first = server.posts[0]
    assert first["__VIEWSTATE"] == ["vs123"]
    assert first["__EVENTVALIDATION"] == ["ev9"]
    assert first["cboYear"] == ["2025"]
    assert first["cboPeriod"] == ["12"]
    for field in ("YEAR", "MONTH", "ORIGIN", "UNIQUE_CARRIER", "PASSENGERS"):
        assert first[field] == ["on"]


def test_failure_raises_with_manual_instructions(tmp_path: Path) -> None:
    with pytest.raises(AcquisitionError) as excinfo:
        provider(tmp_path, FormServer(fail=True)).acquire()
    message = str(excinfo.value)
    assert "manual" in message.lower()
    assert "t100_segment.csv" in message
    assert "PASSENGERS" in message
    assert not (tmp_path / "data/raw/t100/t100_segment.csv").exists()


def write_manual(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "data/raw/t100/t100_segment.csv"
    path.parent.mkdir(parents=True)
    path.write_text(text)
    return path


def test_manual_file_with_matching_checksum_accepted(tmp_path: Path) -> None:
    path = write_manual(tmp_path, "PASSENGERS,UNIQUE_CARRIER,ORIGIN,YEAR,MONTH\n1,AA,ORD,2026,1\n")
    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    server = FormServer()
    f = provider(tmp_path, server, checksum=sha).acquire()
    assert f.pinned
    assert f.path == path
    assert server.posts == []


def test_manual_file_with_wrong_checksum_rejected(tmp_path: Path) -> None:
    write_manual(tmp_path, "PASSENGERS,UNIQUE_CARRIER,ORIGIN,YEAR,MONTH\n1,AA,ORD,2026,1\n")
    with pytest.raises(ChecksumError, match="t100"):
        provider(tmp_path, FormServer(), checksum="0" * 64).acquire()


def test_unpinned_manual_file_accepted_but_marked_unpinned(tmp_path: Path) -> None:
    write_manual(tmp_path, "PASSENGERS,UNIQUE_CARRIER,ORIGIN,YEAR,MONTH\n1,AA,ORD,2026,1\n")
    f = provider(tmp_path, FormServer()).acquire()
    assert not f.pinned


def test_load_passengers_filters_period_and_aggregates(tmp_path: Path) -> None:
    import duckdb

    from flight_pipeline.models import PassengerTraffic, validate_table
    from flight_pipeline.providers.bts_t100 import load_passengers

    path = write_manual(
        tmp_path,
        "PASSENGERS,UNIQUE_CARRIER,ORIGIN,YEAR,MONTH\n"
        "100.00,AA,ORD,2025,12\n"
        "25.00,AA,ORD,2025,12\n"  # second segment row, same airport/carrier/month: summed
        "50.00,UA,ORD,2026,1\n"
        "0.00,UA,CMH,2026,1\n"
        "999.00,AA,ORD,2025,11\n",  # outside the period: dropped
    )
    con = duckdb.connect()
    load_passengers(con, path, MONTHS, "passengers")
    assert validate_table(con, "passengers", PassengerTraffic) == 3
    rows = con.execute("SELECT * FROM passengers ORDER BY year, month, origin, carrier").fetchall()
    assert rows == [
        (2025, 12, "ORD", "AA", 125),
        (2026, 1, "CMH", "UA", 0),
        (2026, 1, "ORD", "UA", 50),
    ]


def test_load_passengers_accepts_header_variants(tmp_path: Path) -> None:
    import duckdb

    from flight_pipeline.providers.bts_t100 import load_passengers

    path = write_manual(tmp_path, "Year,Month,Origin,UniqueCarrier,Passengers\n2026,1,ORD,AA,7\n")
    con = duckdb.connect()
    load_passengers(con, path, MONTHS, "p")
    assert con.execute("SELECT passengers FROM p").fetchall() == [(7,)]


def test_load_passengers_missing_column_fails(tmp_path: Path) -> None:
    import duckdb

    from flight_pipeline.providers.bts_t100 import load_passengers

    path = write_manual(tmp_path, "YEAR,MONTH,ORIGIN,PASSENGERS\n2026,1,ORD,7\n")
    with pytest.raises(AcquisitionError, match="UNIQUE_CARRIER"):
        load_passengers(duckdb.connect(), path, MONTHS, "p")
