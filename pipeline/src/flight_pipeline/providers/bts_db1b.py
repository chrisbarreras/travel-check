"""BTS Airline Origin and Destination Survey, DB1B Market: quarterly pre-zipped files
(research R10).

Only the zip is kept on disk. ``prepare`` extracts each quarter's CSV (about 2 GB), aggregates
it into sold routings and deletes it again.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

import httpx

from flight_pipeline.config import Db1bSourceConfig
from flight_pipeline.providers.base import ChecksumError, SourceFile, verify_checksum
from flight_pipeline.providers.bts_ontime import download


def quarter_key(year: int, quarter: int) -> str:
    return f"{year:04d}-{quarter}"


class BtsDb1bProvider:
    """RoutingSource for the quarterly DB1B Market PREZIP files."""

    def __init__(self, cfg: Db1bSourceConfig, raw_dir: Path, client: httpx.Client) -> None:
        self._cfg = cfg
        self._dir = raw_dir / "db1b"
        self._client = client

    def url_for(self, year: int, quarter: int) -> str:
        return self._cfg.url_pattern.format(year=year, quarter=quarter)

    def path_for(self, year: int, quarter: int) -> Path:
        return self._dir / f"{quarter_key(year, quarter)}.zip"

    def acquire(self, quarters: Iterable[tuple[int, int]]) -> list[SourceFile]:
        return [self._acquire_quarter(y, q) for y, q in quarters]

    def _acquire_quarter(self, year: int, quarter: int) -> SourceFile:
        key = quarter_key(year, quarter)
        url = self.url_for(year, quarter)
        zip_path = self.path_for(year, quarter)
        pinned = self._cfg.checksums.get(key, "")
        fresh = not zip_path.exists()
        if fresh:
            download(self._client, url, zip_path)
        try:
            sha = verify_checksum(zip_path, pinned, f"DB1B {key}")
        except ChecksumError:
            if fresh:
                zip_path.unlink(missing_ok=True)
            raise
        return SourceFile(
            name=f"db1b/{key}", path=zip_path, sha256=sha, url=url, pinned=bool(pinned)
        )
