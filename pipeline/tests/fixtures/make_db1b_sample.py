"""Generate db1b_sample.csv in the real DB1B Market format (research R10).

Run from pipeline/: ``uv run python tests/fixtures/make_db1b_sample.py``. The CSV is committed;
this script documents how each row was built. Expected results are written by hand in
expected/sold_routings.json. See README.md for the case list.
"""

from __future__ import annotations

import csv
from pathlib import Path

# The real header of Origin_and_Destination_Survey_DB1BMarket_{year}_{quarter}.csv, including
# the trailing empty column (every line ends with a comma).
HEADER = [
    "ItinID",
    "MktID",
    "MktCoupons",
    "Year",
    "Quarter",
    "OriginAirportID",
    "OriginAirportSeqID",
    "OriginCityMarketID",
    "Origin",
    "OriginCountry",
    "OriginStateFips",
    "OriginState",
    "OriginStateName",
    "OriginWac",
    "DestAirportID",
    "DestAirportSeqID",
    "DestCityMarketID",
    "Dest",
    "DestCountry",
    "DestStateFips",
    "DestState",
    "DestStateName",
    "DestWac",
    "AirportGroup",
    "WacGroup",
    "TkCarrierChange",
    "TkCarrierGroup",
    "OpCarrierChange",
    "OpCarrierGroup",
    "RPCarrier",
    "TkCarrier",
    "OpCarrier",
    "BulkFare",
    "Passengers",
    "MktFare",
    "MktDistance",
    "MktDistanceGroup",
    "MktMilesFlown",
    "NonStopMiles",
    "ItinGeoType",
    "MktGeoType",
    "",
]

# (case, year, quarter, coupons, airport group, ticketing carrier group, passengers)
ROWS = [
    ("san_q1", 2026, 1, 2, "CMH:ORD:SAN", "AA:AA", 20),
    ("san_q4", 2025, 4, 2, "CMH:ORD:SAN", "AA:AA", 15),  # same routing, earlier quarter
    ("sea_partner", 2026, 1, 2, "CMH:ORD:SEA", "AA:AS", 40),
    ("den_below_min", 2026, 1, 2, "CMH:ORD:DEN", "AA:AA", 12),
    ("phx", 2026, 1, 2, "CMH:ORD:PHX", "AA:AA", 50),
    ("ua_den", 2026, 1, 2, "CMH:ORD:DEN", "UA:UA", 60),
    ("wn_den", 2026, 1, 2, "CMH:ORD:DEN", "WN:WN", 45),  # renumbering airline, sold
    ("dl_ua", 2026, 1, 2, "CMH:ORD:SAN", "DL:UA", 30),  # sold, but not a partner pair
    ("legacy_code", 2026, 1, 2, "CMH:ORD:SAN", "US:AA", 4),  # mapped to AA:AA by carrier_map
    ("unknown_out", 2026, 1, 2, "CMH:ORD:SAN", "AA:--", 5),
    ("unknown_in", 2026, 1, 2, "CMH:ORD:SAN", "--:AA", 3),
    ("one_coupon", 2026, 1, 1, "CMH:ORD", "AA", 100),
    ("three_coupons", 2026, 1, 3, "CMH:ORD:DEN:SAN", "AA:AA:AA", 50),
]


def render(i: int, row: tuple[str, int, int, int, str, str, int]) -> list[str]:
    _case, year, quarter, coupons, airports, carriers, pax = row
    codes = airports.split(":")
    legs = carriers.split(":")
    itin = f"{year}{quarter}{i:08d}"
    known = [c for c in legs if c != "--"]
    return [
        itin,
        f"{itin}01",
        str(coupons),
        str(year),
        str(quarter),
        "10000",
        "1000001",
        "30000",
        codes[0],
        "US",
        "39",
        "OH",
        "Ohio",
        "44",
        "20000",
        "2000001",
        "31000",
        codes[-1],
        "US",
        "06",
        "CA",
        "California",
        "91",
        airports,
        ":".join("44" for _ in codes),
        "0.00" if len(set(legs)) == 1 else "1.00",
        carriers,
        "0.00" if len(set(legs)) == 1 else "1.00",
        carriers,
        known[0] if known else "--",
        known[0] if known else "--",
        known[0] if known else "--",
        "0.00",
        f"{pax}.00",
        "250.00",
        "1800.00",
        "4",
        "1800.00",
        "1700.00",
        "2",
        "2",
        "",
    ]


def main() -> None:
    path = Path(__file__).parent / "db1b_sample.csv"
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(HEADER)
        for i, row in enumerate(ROWS, start=1):
            w.writerow(render(i, row))
    print(f"wrote {path}")


if __name__ == "__main__":
    main()
