"""Provider interfaces (constitution Principle VI).

Callers depend only on these protocols, so a licensed source can replace a free one without
changing them.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


class AcquisitionError(RuntimeError):
    """A source could not be obtained. The message tells the user what to do next."""


class ChecksumError(AcquisitionError):
    """A file's SHA-256 does not match the checksum pinned in configuration."""


@dataclass(frozen=True)
class SourceFile:
    """One acquired raw file, with the checksum recorded in the run manifest."""

    name: str  # e.g. "ontime/2026-09" or "t100"
    path: Path
    sha256: str
    url: str | None
    pinned: bool


@dataclass(frozen=True)
class TimezoneEntry:
    tz: str
    source: str


class OnTimeSource(Protocol):
    def acquire(self, months: Iterable[tuple[int, int]]) -> list[SourceFile]:
        """Obtain one CSV per month, downloading only what is missing or unverified."""
        ...


class RoutingSource(Protocol):
    def acquire(self, quarters: Iterable[tuple[int, int]]) -> list[SourceFile]:
        """Obtain one archive of sold ticket routings per quarter (DB1B Market)."""
        ...


class PassengerSource(Protocol):
    def acquire(self) -> SourceFile:
        """Obtain the passenger traffic CSV."""
        ...


class TimezoneSource(Protocol):
    def lookup(self, codes: Iterable[str]) -> Mapping[str, TimezoneEntry]:
        """Return the IANA zone for every code, or raise MissingTimezoneError."""
        ...


def sha256_file(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while block := f.read(chunk):
            h.update(block)
    return h.hexdigest()


def verify_checksum(path: Path, pinned: str, label: str) -> str:
    """Return the file's SHA-256. If a checksum is pinned (non-empty), it must match."""
    actual = sha256_file(path)
    if pinned and actual.lower() != pinned.lower():
        raise ChecksumError(
            f"{label}: SHA-256 of {path} is {actual}, but configuration pins {pinned}. "
            "The source file changed or is corrupt; delete it to re-acquire, or update the "
            "pinned checksum deliberately."
        )
    return actual
