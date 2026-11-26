"""Published showcase files (specs/002 contracts/outputs.md, FR-011, FR-014, FR-015,
FR-015a, FR-025)."""

from __future__ import annotations

import json
import random
from pathlib import Path

import pytest

from flight_pipeline.showcase.models import NOT_COVERED_KINDS, RouteFile, ShowcaseIndex
from flight_pipeline.showcase.publish import (
    MEASURES,
    PublishError,
    gzip_size,
    landing_file,
    render,
    stable_bytes,
    wording_violations,
    write_files,
)
from tests.unit.showcase_factory import (
    CONTEXT,
    PERIOD,
    A,
    B,
    C,
    index,
    itinerary,
    rate,
    route_file,
)


def test_stable_bytes_are_sorted_compact_lf_and_rounded() -> None:
    data = stable_bytes({"b": 1.23456789, "a": [0.1 + 0.2, -0.0000001], "c": "é"})
    assert data == '{"a":[0.3,0.0],"b":1.234568,"c":"é"}\n'.encode()
    assert b"\r" not in data
    assert stable_bytes({"b": 1, "a": 2}) == stable_bytes({"a": 2, "b": 1})


def test_render_is_deterministic() -> None:
    first = render(index(), [route_file()], CONTEXT)
    second = render(index(), [route_file()], CONTEXT)
    assert first == second
    assert set(first) == {"index.json", "landing.json", "routes/CMH-SAN.json"}


def test_validation_failure_stops_the_run() -> None:
    # valid without context, but below the configured minimum sample of 30 days
    small = itinerary(A, paired=10, feasible=9)
    assert small.result.status == "ok"
    route = route_file(itineraries=[small, itinerary(B, "DEN"), itinerary(C, "DFW")])
    with pytest.raises(PublishError, match="fails validation"):
        render(index([route]), [route], CONTEXT)


def test_index_and_route_files_must_agree() -> None:
    other = route_file("BOI-SEA")
    with pytest.raises(PublishError, match="differ"):
        render(index([route_file()]), [route_file(), other], CONTEXT)


def test_size_budgets_on_gzip_bytes_report_each_file(tmp_path: Path) -> None:
    files = render(index(), [route_file()], CONTEXT)
    sizes = write_files(tmp_path, files, 2048, 150)
    assert sizes == {name: gzip_size(b) for name, b in files.items()}
    assert (tmp_path / "routes" / "CMH-SAN.json").read_bytes() == files["routes/CMH-SAN.json"]
    with pytest.raises(PublishError, match=r"above the 0 KB budget.*routes/CMH-SAN\.json"):
        write_files(tmp_path / "small", files, 0, 0)
    noise = random.Random(1).randbytes(200_000)  # incompressible
    big = dict(files, **{"landing.json": noise})
    with pytest.raises(PublishError, match="landing budget"):
        write_files(tmp_path / "landing", big, 2048, 150)


def test_stale_route_files_are_removed(tmp_path: Path) -> None:
    (tmp_path / "routes").mkdir()
    (tmp_path / "routes" / "OLD-RTE.json").write_text("{}")
    write_files(tmp_path, render(index(), [route_file()], CONTEXT), 2048, 150)
    assert not (tmp_path / "routes" / "OLD-RTE.json").exists()


def test_landing_file_is_self_contained() -> None:
    files = render(index(), [route_file()], CONTEXT)
    landing = RouteFile.model_validate_json(files["landing.json"], context=CONTEXT)
    assert [c.comparison_id for c in landing.comparisons] == [f"{A}|{B}"]
    assert {i.itinerary_id for i in landing.itineraries} == {A, B}
    assert landing.period == PERIOD


def test_insights_may_name_itineraries_outside_the_file() -> None:
    from flight_pipeline.showcase.models import Alternative

    alt = Alternative(
        itinerary_id="CMH-ATL-SAN:DL0900+DL1300",  # on the route, not in the file
        minutes_saved=20,
        rate_this=rate(40, 36),
        rate_other=rate(40, 36),
        ci_low=-0.01,
        ci_high=0.02,
        shared_days=40,
    )
    route = route_file(
        itineraries=[
            itinerary(A, faster_alternatives=[alt]),
            itinerary(B, "DEN", feasible=28),
            itinerary(C, "DFW", feasible=20),
        ]
    )
    landing = landing_file(route, f"{A}|{B}")
    assert {i.itinerary_id for i in landing.itineraries} == {A, B}
    assert landing.itineraries[0].faster_alternatives == [alt]


def test_coverage_states_every_not_covered_kind() -> None:
    files = render(index(), [route_file()], CONTEXT)
    idx = ShowcaseIndex.model_validate_json(files["index.json"])
    assert sorted(n.kind for n in idx.coverage.not_covered) == sorted(NOT_COVERED_KINDS)
    assert all(n.text for n in idx.coverage.not_covered)
    assert idx.coverage.routes == ["CMH-SAN"]


def test_definitions_cover_every_measure() -> None:
    idx = index()
    keys = {d.key for d in idx.definitions}
    assert keys >= MEASURES
    for measure in (
        "connection_feasibility",
        "slack",
        "buffer",
        "faster_alternative",
        "monthly_rate",
        "failure_types",
        "schedule_change",
        "nonstop_ratio",
    ):
        assert measure in keys
    assert all(d.methodology_anchor.startswith("docs/methodology.md#") for d in idx.definitions)


def test_attribution_names_required_sources() -> None:
    sources = {a.source for a in index().attribution}
    assert {"BTS", "airportsdata", "tzdata"} <= sources


@pytest.mark.parametrize(
    "text",
    [
        "The probability of connecting",
        "You will make this connection",
        "Passengers missed their connection",
        "likely to connect",
        "a chance of a tight connection",
    ],
)
def test_forbidden_wording_is_found_anywhere(text: str) -> None:
    found = wording_violations({"a": [{"b": text}]})
    assert found
    assert found[0].startswith("$.a[0].b")


def test_forbidden_wording_in_keys_and_allowed_disclaimers() -> None:
    assert wording_violations({"success_probability": 1})
    assert not wording_violations({"t": "a historical frequency, not a prediction"})
    assert not wording_violations({"t": "worked on 92% of days in the data period"})


def test_every_published_text_passes_the_scan() -> None:
    files = render(index(), [route_file()], CONTEXT)
    for data in files.values():
        assert wording_violations(json.loads(data)) == []


def test_forbidden_wording_stops_the_run() -> None:
    idx = index()
    bad = idx.model_copy(
        update={"landing": idx.landing.model_copy(update={"reason": "the likely winner"})}
    )
    with pytest.raises(PublishError, match="forbidden wording"):
        render(bad, [route_file()], CONTEXT)
