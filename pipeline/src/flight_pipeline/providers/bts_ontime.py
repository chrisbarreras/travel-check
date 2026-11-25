"""BTS Marketing Carrier On-Time Performance: monthly pre-zipped files (research R1)."""

from __future__ import annotations

import shutil
import zipfile
from collections.abc import Iterable
from pathlib import Path

import httpx

from flight_pipeline.config import OnTimeSourceConfig
from flight_pipeline.providers.base import (
    AcquisitionError,
    ChecksumError,
    SourceFile,
    verify_checksum,
)


def month_key(year: int, month: int) -> str:
    return f"{year:04d}-{month:02d}"


def download(client: httpx.Client, url: str, dest: Path) -> None:
    """Stream ``url`` to ``dest`` atomically (via a .part file)."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_suffix(dest.suffix + ".part")
    try:
        with client.stream("GET", url, follow_redirects=True, timeout=300.0) as resp:
            if resp.status_code != 200:
                raise AcquisitionError(f"download failed: HTTP {resp.status_code} for {url}")
            with part.open("wb") as f:
                for chunk in resp.iter_bytes(1 << 20):
                    f.write(chunk)
    except httpx.HTTPError as exc:
        part.unlink(missing_ok=True)
        raise AcquisitionError(f"download failed for {url}: {exc}") from exc
    except AcquisitionError:
        part.unlink(missing_ok=True)
        raise
    part.replace(dest)


def extract_single_csv(zip_path: Path, csv_path: Path) -> None:
    """Extract the archive's only CSV member to ``csv_path``. Member names are never used
    as paths, so an archive cannot write outside the raw data directory."""
    try:
        with zipfile.ZipFile(zip_path) as zf:
            members = [m for m in zf.infolist() if m.filename.lower().endswith(".csv")]
            if len(members) != 1:
                raise AcquisitionError(
                    f"{zip_path} should contain exactly one CSV file, found {len(members)}"
                )
            part = csv_path.with_suffix(".csv.part")
            with zf.open(members[0]) as src, part.open("wb") as dst:
                shutil.copyfileobj(src, dst, 1 << 20)
            part.replace(csv_path)
    except zipfile.BadZipFile as exc:
        raise AcquisitionError(f"{zip_path} is not a valid zip archive: {exc}") from exc


class BtsOnTimeProvider:
    """OnTimeSource for the monthly PREZIP files."""

    def __init__(self, cfg: OnTimeSourceConfig, raw_dir: Path, client: httpx.Client) -> None:
        self._cfg = cfg
        self._dir = raw_dir / "ontime"
        self._client = client

    def url_for(self, year: int, month: int) -> str:
        key = month_key(year, month)
        if key in self._cfg.overrides:
            return self._cfg.overrides[key]
        return self._cfg.url_pattern.format(year=year, month=month)

    def acquire(self, months: Iterable[tuple[int, int]]) -> list[SourceFile]:
        return [self._acquire_month(y, m) for y, m in months]

    def _acquire_month(self, year: int, month: int) -> SourceFile:
        key = month_key(year, month)
        url = self.url_for(year, month)
        zip_path = self._dir / f"{key}.zip"
        csv_path = self._dir / f"{key}.csv"
        pinned = self._cfg.checksums.get(key, "")
        fresh = not zip_path.exists()
        if fresh:
            download(self._client, url, zip_path)
        try:
            sha = verify_checksum(zip_path, pinned, f"on-time {key}")
        except ChecksumError:
            if fresh:
                zip_path.unlink(missing_ok=True)
            raise
        if fresh or not csv_path.exists():
            extract_single_csv(zip_path, csv_path)
        return SourceFile(
            name=f"ontime/{key}", path=csv_path, sha256=sha, url=url, pinned=bool(pinned)
        )
