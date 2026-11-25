"""Phase 0 BTS connection feasibility experiment: pipeline library."""

import zoneinfo

__version__ = "0.1.0"

# Time-zone rules come only from the pinned tzdata package, never from a system database, so
# results and the manifest's tzdata version agree on every operating system (research R3).
zoneinfo.reset_tzpath(to=[])
