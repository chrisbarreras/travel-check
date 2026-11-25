"""Monthly on-time zip download (research R1). No network: httpx MockTransport."""

import hashlib
import io
import zipfile
from pathlib import Path

import httpx
import pytest

from flight_pipeline.config import OnTimeSourceConfig
from flight_pipeline.providers.base import AcquisitionError, ChecksumError
from flight_pipeline.providers.bts_ontime import BtsOnTimeProvider

PATTERN = "https://example.test/PREZIP/OnTime_{year}_{month}.zip"


def make_zip(csv_text: str, name: str = "data.csv") -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(name, csv_text)
        zf.writestr("readme.html", "<html></html>")
    return buf.getvalue()


class Server:
    def __init__(self, files: dict[str, bytes]) -> None:
        self.files = files
        self.requests: list[str] = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        self.requests.append(url)
        if url in self.files:
            return httpx.Response(200, content=self.files[url])
        return httpx.Response(404)

    def client(self) -> httpx.Client:
        return httpx.Client(transport=httpx.MockTransport(self.handler))


def provider(
    tmp_path: Path,
    server: Server,
    overrides: dict[str, str] | None = None,
    checksums: dict[str, str] | None = None,
) -> BtsOnTimeProvider:
    cfg = OnTimeSourceConfig(
        url_pattern=PATTERN, overrides=overrides or {}, checksums=checksums or {}
    )
    return BtsOnTimeProvider(cfg, tmp_path / "raw", server.client())


def test_url_uses_non_padded_month(tmp_path: Path) -> None:
    p = provider(tmp_path, Server({}))
    assert p.url_for(2026, 3) == "https://example.test/PREZIP/OnTime_2026_3.zip"
    assert p.url_for(2025, 11) == "https://example.test/PREZIP/OnTime_2025_11.zip"


def test_override_url_used(tmp_path: Path) -> None:
    p = provider(tmp_path, Server({}), overrides={"2023-12": "https://example.test/odd(1).zip"})
    assert p.url_for(2023, 12) == "https://example.test/odd(1).zip"


def test_download_extract_and_record_checksum(tmp_path: Path) -> None:
    content = make_zip("a,b\n1,2\n")
    server = Server({"https://example.test/PREZIP/OnTime_2026_3.zip": content})
    files = provider(tmp_path, server).acquire([(2026, 3)])
    assert len(files) == 1
    f = files[0]
    assert f.name == "ontime/2026-03"
    assert f.sha256 == hashlib.sha256(content).hexdigest()
    assert not f.pinned
    assert f.path.read_text() == "a,b\n1,2\n"
    assert f.path.name == "2026-03.csv"


def test_pinned_checksum_mismatch_fails(tmp_path: Path) -> None:
    server = Server({"https://example.test/PREZIP/OnTime_2026_3.zip": make_zip("x\n")})
    p = provider(tmp_path, server, checksums={"2026-03": "0" * 64})
    with pytest.raises(ChecksumError, match="2026-03"):
        p.acquire([(2026, 3)])
    assert not (tmp_path / "raw" / "ontime" / "2026-03.zip").exists()


def test_pinned_checksum_match_is_marked_pinned(tmp_path: Path) -> None:
    content = make_zip("x\n")
    server = Server({"https://example.test/PREZIP/OnTime_2026_3.zip": content})
    sha = hashlib.sha256(content).hexdigest()
    [f] = provider(tmp_path, server, checksums={"2026-03": sha}).acquire([(2026, 3)])
    assert f.pinned


def test_present_verified_file_not_downloaded_again(tmp_path: Path) -> None:
    content = make_zip("x\n")
    url = "https://example.test/PREZIP/OnTime_2026_3.zip"
    sha = hashlib.sha256(content).hexdigest()
    first = Server({url: content})
    provider(tmp_path, first, checksums={"2026-03": sha}).acquire([(2026, 3)])
    second = Server({url: content})
    [f] = provider(tmp_path, second, checksums={"2026-03": sha}).acquire([(2026, 3)])
    assert second.requests == []
    assert f.sha256 == sha


def test_present_file_with_wrong_pinned_checksum_fails(tmp_path: Path) -> None:
    url = "https://example.test/PREZIP/OnTime_2026_3.zip"
    provider(tmp_path, Server({url: make_zip("x\n")})).acquire([(2026, 3)])
    with pytest.raises(ChecksumError):
        provider(tmp_path, Server({}), checksums={"2026-03": "f" * 64}).acquire([(2026, 3)])


def test_http_error_is_acquisition_error(tmp_path: Path) -> None:
    with pytest.raises(AcquisitionError, match="OnTime_2026_4"):
        provider(tmp_path, Server({})).acquire([(2026, 4)])


def test_zip_without_single_csv_fails(tmp_path: Path) -> None:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("readme.html", "x")
    server = Server({"https://example.test/PREZIP/OnTime_2026_3.zip": buf.getvalue()})
    with pytest.raises(AcquisitionError, match="CSV"):
        provider(tmp_path, server).acquire([(2026, 3)])


def test_zip_member_path_is_not_trusted(tmp_path: Path) -> None:
    server = Server(
        {"https://example.test/PREZIP/OnTime_2026_3.zip": make_zip("x\n", "../../evil.csv")}
    )
    [f] = provider(tmp_path, server).acquire([(2026, 3)])
    assert f.path == tmp_path / "raw" / "ontime" / "2026-03.csv"
    assert not (tmp_path / "evil.csv").exists()
