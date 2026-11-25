"""Quarterly DB1B Market zip download (research R10). No network: httpx MockTransport."""

import hashlib
from pathlib import Path

import pytest

from flight_pipeline.config import Db1bSourceConfig
from flight_pipeline.providers.base import AcquisitionError, ChecksumError
from flight_pipeline.providers.bts_db1b import BtsDb1bProvider, quarter_key
from tests.unit.test_provider_ontime import Server, make_zip

PATTERN = "https://example.test/PREZIP/DB1BMarket_{year}_{quarter}.zip"
URL = "https://example.test/PREZIP/DB1BMarket_2025_2.zip"


def provider(tmp_path: Path, server: Server, checksums: dict[str, str] | None = None):
    cfg = Db1bSourceConfig(url_pattern=PATTERN, checksums=checksums or {})
    return BtsDb1bProvider(cfg, tmp_path / "raw", server.client())


def test_quarter_key_and_url(tmp_path: Path) -> None:
    assert quarter_key(2024, 3) == "2024-3"
    assert provider(tmp_path, Server({})).url_for(2025, 2) == URL


def test_download_keeps_zip_and_records_checksum(tmp_path: Path) -> None:
    content = make_zip("a,b\n1,2\n")
    [f] = provider(tmp_path, Server({URL: content})).acquire([(2025, 2)])
    assert f.name == "db1b/2025-2"
    assert f.path == tmp_path / "raw" / "db1b" / "2025-2.zip"
    assert f.path.read_bytes() == content  # extracted later by prepare, then deleted
    assert f.sha256 == hashlib.sha256(content).hexdigest()
    assert f.url == URL
    assert not f.pinned


def test_pinned_checksum_match_is_marked_pinned(tmp_path: Path) -> None:
    content = make_zip("x\n")
    sha = hashlib.sha256(content).hexdigest()
    [f] = provider(tmp_path, Server({URL: content}), {"2025-2": sha}).acquire([(2025, 2)])
    assert f.pinned


def test_pinned_checksum_mismatch_fails_and_removes_download(tmp_path: Path) -> None:
    server = Server({URL: make_zip("x\n")})
    with pytest.raises(ChecksumError, match="2025-2"):
        provider(tmp_path, server, {"2025-2": "0" * 64}).acquire([(2025, 2)])
    assert not (tmp_path / "raw" / "db1b" / "2025-2.zip").exists()


def test_present_verified_file_not_downloaded_again(tmp_path: Path) -> None:
    content = make_zip("x\n")
    sha = hashlib.sha256(content).hexdigest()
    provider(tmp_path, Server({URL: content}), {"2025-2": sha}).acquire([(2025, 2)])
    second = Server({URL: content})
    [f] = provider(tmp_path, second, {"2025-2": sha}).acquire([(2025, 2)])
    assert second.requests == []
    assert f.sha256 == sha


def test_present_file_with_wrong_pinned_checksum_fails(tmp_path: Path) -> None:
    provider(tmp_path, Server({URL: make_zip("x\n")})).acquire([(2025, 2)])
    with pytest.raises(ChecksumError):
        provider(tmp_path, Server({}), {"2025-2": "f" * 64}).acquire([(2025, 2)])


def test_http_error_is_acquisition_error(tmp_path: Path) -> None:
    with pytest.raises(AcquisitionError, match="DB1BMarket_2025_2"):
        provider(tmp_path, Server({})).acquire([(2025, 2)])
