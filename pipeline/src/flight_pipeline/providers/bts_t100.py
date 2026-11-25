"""BTS T-100 Domestic Segment (U.S. Carriers) passenger data (research R2).

T-100 has no pre-zipped file. The scripted path submits the TranStats download form once per
month and combines the months into the configured file. If that fails, the run stops with
instructions for a one-time manual download into the same path. Either way the combined CSV
is what gets checksummed (the generated zip files carry fresh timestamps on every download).
"""

from __future__ import annotations

import csv
import io
import re
import zipfile
from collections.abc import Sequence
from pathlib import Path

import duckdb
import httpx

from flight_pipeline.config import T100SourceConfig
from flight_pipeline.providers.base import (
    AcquisitionError,
    ChecksumError,
    SourceFile,
    verify_checksum,
)

FORM_URL = (
    "https://www.transtats.bts.gov/DL_SelectFields.aspx?gnoyr_VQ=FIM&QO_fu146_anzr=Nv4%20Pn44vr45"
)
FIELDS = ("PASSENGERS", "UNIQUE_CARRIER", "ORIGIN", "YEAR", "MONTH")
_HIDDEN_RE = re.compile(r"<input[^>]*>", re.IGNORECASE)
_ATTR_RE = re.compile(r'(\w+)="([^"]*)"')


def _hidden_fields(html: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for tag in _HIDDEN_RE.findall(html):
        attrs = dict(_ATTR_RE.findall(tag))
        if attrs.get("type", "").lower() == "hidden" and "name" in attrs:
            out[attrs["name"]] = attrs.get("value", "")
    return out


def _manual_instructions(target: Path, months: Sequence[tuple[int, int]]) -> str:
    (sy, sm), (ey, em) = months[0], months[-1]
    return (
        "Manual download needed for T-100 passenger data:\n"
        f"  1. Open {FORM_URL}\n"
        f"  2. Tick the fields {', '.join(FIELDS)}; Geography: All.\n"
        f"  3. Download each year covering {sy}-{sm:02d} to {ey}-{em:02d} with Period "
        "'All Months' and unzip the data CSV (not Documentation.csv).\n"
        f"  4. Combine them into one CSV with a single header row, saved as {target}\n"
        "  5. Rerun; the file's SHA-256 is printed so you can pin it in [sources.t100] checksum."
    )


def _data_csv(content: bytes) -> str:
    with zipfile.ZipFile(io.BytesIO(content)) as zf:
        names = [
            n
            for n in zf.namelist()
            if n.lower().endswith(".csv") and "documentation" not in n.lower()
        ]
        if len(names) != 1:
            raise AcquisitionError(f"expected one data CSV in the T-100 archive, found {names}")
        return zf.read(names[0]).decode("utf-8-sig")


class BtsT100Provider:
    """PassengerSource for T-100 segment data."""

    def __init__(
        self,
        cfg: T100SourceConfig,
        target: Path,
        months: Sequence[tuple[int, int]],
        client: httpx.Client,
    ) -> None:
        self._cfg = cfg
        self._target = target
        self._months = list(months)
        self._client = client

    def acquire(self) -> SourceFile:
        if not self._target.exists():
            try:
                self._scripted_download()
            except (AcquisitionError, httpx.HTTPError, zipfile.BadZipFile, KeyError) as exc:
                raise AcquisitionError(
                    f"scripted T-100 download failed ({exc}).\n"
                    + _manual_instructions(self._target, self._months)
                ) from exc
            fresh = True
        else:
            fresh = False
        try:
            sha = verify_checksum(self._target, self._cfg.checksum, "t100")
        except ChecksumError:
            if fresh:
                self._target.unlink(missing_ok=True)
            raise
        return SourceFile(
            name="t100",
            path=self._target,
            sha256=sha,
            url=FORM_URL,
            pinned=bool(self._cfg.checksum),
        )

    def _scripted_download(self) -> None:
        header: list[str] | None = None
        rows: list[list[str]] = []
        for year, month in self._months:
            page = self._client.get(FORM_URL, follow_redirects=True, timeout=120.0)
            page.raise_for_status()
            form = _hidden_fields(page.text)
            if "__VIEWSTATE" not in form:
                raise AcquisitionError("TranStats form page has no __VIEWSTATE field")
            form.update(
                {
                    "cboGeography": "All",
                    "cboYear": str(year),
                    "cboPeriod": str(month),
                    "chkDownloadZip": "on",
                    "btnDownload": "Download",
                    **dict.fromkeys(FIELDS, "on"),
                }
            )
            resp = self._client.post(FORM_URL, data=form, follow_redirects=True, timeout=300.0)
            resp.raise_for_status()
            if "zip" not in resp.headers.get("content-type", ""):
                raise AcquisitionError(
                    f"TranStats returned {resp.headers.get('content-type')} instead of a zip "
                    f"for {year}-{month:02d}"
                )
            reader = csv.reader(io.StringIO(_data_csv(resp.content)))
            month_header = next(reader)
            if header is None:
                header = month_header
            elif month_header != header:
                raise AcquisitionError(f"T-100 header changed between months: {month_header}")
            rows.extend(r for r in reader if r)
        if header is None:
            raise AcquisitionError("no T-100 months requested")
        self._target.parent.mkdir(parents=True, exist_ok=True)
        part = self._target.with_suffix(".csv.part")
        with part.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f, lineterminator="\n")
            writer.writerow(header)
            writer.writerows(rows)
        part.replace(self._target)


def _norm(name: str) -> str:
    return name.strip().lower().replace("_", "")


def load_passengers(
    con: duckdb.DuckDBPyConnection,
    csv_path: Path,
    months: Sequence[tuple[int, int]],
    table: str,
) -> None:
    """Create ``table`` (PassengerTraffic rows): passengers boarded summed by year, month,
    origin and carrier, for the given months only. Header names are matched ignoring case
    and underscores, so both form and manual downloads work."""
    rel = con.read_csv(str(csv_path), all_varchar=True, header=True)
    by_norm = {_norm(c): c for c in rel.columns}
    wanted = {
        "year": "YEAR",
        "month": "MONTH",
        "origin": "ORIGIN",
        "uniquecarrier": "UNIQUE_CARRIER",
        "passengers": "PASSENGERS",
    }
    missing = [label for key, label in wanted.items() if key not in by_norm]
    if missing:
        raise AcquisitionError(f"{csv_path} is missing T-100 column(s): {', '.join(missing)}")
    col = {key: '"' + by_norm[key].replace('"', '""') + '"' for key in wanted}
    month_list = ", ".join(f"({y}, {m})" for y, m in months)
    con.register("_t100_raw", rel)
    con.execute(
        f"""
        CREATE OR REPLACE TABLE {table} AS
        WITH typed AS (
            SELECT CAST({col["year"]} AS INTEGER) AS year,
                   CAST({col["month"]} AS INTEGER) AS month,
                   trim({col["origin"]}) AS origin,
                   trim({col["uniquecarrier"]}) AS carrier,
                   CAST(round(CAST({col["passengers"]} AS DOUBLE)) AS BIGINT) AS passengers
            FROM _t100_raw
        )
        SELECT year, month, origin, carrier, CAST(sum(passengers) AS BIGINT) AS passengers
        FROM typed
        WHERE (year, month) IN (SELECT * FROM (VALUES {month_list}))
        GROUP BY ALL
        ORDER BY year, month, origin, carrier
        """
    )
    con.unregister("_t100_raw")
