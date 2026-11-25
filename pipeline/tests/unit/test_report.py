"""Report sections (contracts/outputs.md reporting rules, FR-012, FR-032)."""

import json
import re
from pathlib import Path
from typing import Any

from flight_pipeline.config import Hubs
from flight_pipeline.hubs import select_hubs
from flight_pipeline.report import hub_section
from tests.unit.test_hub_selection import hubs_cfg, metrics

FIXTURE = json.loads(
    (Path(__file__).resolve().parents[1] / "fixtures" / "hub_metrics.json").read_text()
)


def hub_report(cfg: Hubs | None = None) -> str:
    result = select_hubs(metrics(), cfg or hubs_cfg())
    return hub_section(
        result.candidates, result.selection, result.unmet, result.median_weather_share
    )


def test_hub_section_lists_every_candidate_with_metrics() -> None:
    text = hub_report()
    for c in FIXTURE["candidates"]:
        assert re.search(rf"\| \d+ \| {c['airport']} \|", text), c["airport"]
    assert "| 1 | PHX | 3.000 | no (5) |" in text


def test_hub_section_gives_reason_for_each_selected_hub() -> None:
    text = hub_report()
    assert "SEA" in text
    assert "airline coverage: AS" in text
    assert "winter weather peak" in text
    assert text.count("selected (") == 5


def test_hub_section_reports_missing_passengers() -> None:
    assert "missing (scored as 0)" in hub_report()


def test_hub_section_names_unmet_constraints() -> None:
    assert "**Unmet constraints:** none" in hub_report()
    text = hub_report(hubs_cfg(min_winter_peak=5))
    assert "**Unmet constraints:**" in text
    assert "weather_winter" in text


def od_rows() -> list[Any]:
    from flight_pipeline.models import OdSelection

    return [
        OdSelection(
            origin="CMH",
            dest="SAN",
            comparable_pairs=4,
            main_hub="ORD",
            regional_origin=True,
            rank=1,
            selected=True,
        ),
        OdSelection(
            origin="ORD",
            dest="BOS",
            comparable_pairs=3,
            main_hub="DFW",
            regional_origin=False,
            rank=2,
            selected=True,
        ),
        OdSelection(
            origin="BOI",
            dest="SEA",
            comparable_pairs=1,
            main_hub="ORD",
            regional_origin=True,
            rank=3,
            selected=False,
        ),
    ]


def test_od_section_lists_selected_pairs_with_rank_and_counts() -> None:
    from flight_pipeline.report import od_section

    text = od_section(od_rows(), {("CMH", "SAN"): 5, ("ORD", "BOS"): 3, ("BOI", "SEA"): 2}, [], [])
    assert "| 1 | CMH-SAN | yes | ORD | 4 | 5 |" in text
    assert "| 2 | ORD-BOS | no | DFW | 3 | 3 |" in text
    assert "BOI-SEA" not in text.split("**Not selected")[0]
    assert "1 of 2 selected pairs have a regional origin" in text


def test_od_section_reports_pairs_without_itineraries_and_shortfalls() -> None:
    from flight_pipeline.report import od_section

    text = od_section(
        od_rows(), {}, ["only 2 of 15 pairs could be selected"], ["BOI-SEA (mct45_cut15_rec75)"]
    )
    assert "only 2 of 15 pairs could be selected" in text
    assert "**Pairs without qualifying itineraries:** BOI-SEA (mct45_cut15_rec75)" in text
    text = od_section(od_rows(), {}, [], [])
    assert "**Pairs without qualifying itineraries:** none" in text


FORBIDDEN = (
    "made the connection",
    "made their connection",
    "missed their connection",
    "passengers made",
    "passengers missed",
    "probability",
    "chance of making",
    "will be feasible",
    "on-time arrival",
)


def result_row(itinerary: str, paired: int, feasible: int, **kw: Any) -> Any:
    import datetime as dt

    from flight_pipeline.models import ItineraryResult

    ok = paired >= 30
    base: dict[str, Any] = dict(
        itinerary_id=itinerary,
        scenario_id="mct30_cut15_rec60",
        paired_days=paired,
        excluded_not_connecting=1,
        excluded_quality=2,
        feasibility_rate=round(feasible / paired, 6) if ok else None,
        status="ok" if ok else "insufficient_data",
        count_feasible=feasible,
        count_insufficient_time=paired - feasible - 3,
        count_cancelled=2,
        count_diverted=1,
        slack_min=-20,
        slack_p10=15,
        slack_p50=60,
        slack_p90=110,
        period_start=dt.date(2025, 10, 1),
        period_end=dt.date(2026, 9, 30),
    )
    base.update(kw)
    return ItineraryResult(**base)


def results_text() -> str:
    from flight_pipeline.report import results_section

    rows = [
        result_row("CMH-ORD-SAN:AA1+AA2", 300, 240),
        result_row("CMH-DFW-SAN:AA3+AA4", 20, 15),
    ]
    return results_section(rows, {"CMH-ORD-SAN:AA1+AA2": "ORD", "CMH-DFW-SAN:AA3+AA4": "DFW"}, 30)


def test_results_show_sample_size_and_period_with_every_rate() -> None:
    text = results_text()
    assert "80% (240 of 300 days)" in text
    assert "2025-10-01 to 2026-09-30" in text


def test_results_below_minimum_show_insufficient_data_and_no_rate() -> None:
    text = results_text()
    line = next(line for line in text.splitlines() if "CMH-DFW-SAN:AA3+AA4" in line)
    assert "insufficient data (20 days)" in line
    assert "%" not in line.split("|")[3]


def test_results_report_failures_and_slack_separately() -> None:
    line = next(line for line in results_text().splitlines() if "CMH-ORD-SAN:AA1+AA2" in line)
    assert "| 57 | 2 | 1 |" in line  # insufficient time, cancelled, diverted
    assert "-20 / 15 / 60 / 110" in line
    assert "| 1 / 2 |" in line  # excluded: not connecting / quality


def test_results_use_feasibility_wording_only() -> None:
    text = results_text().lower()
    assert "connection feasibility" in text
    assert "historical" in text
    for phrase in FORBIDDEN:
        assert phrase not in text, phrase


def pair(a: str, b: str, **kw: Any) -> Any:
    from flight_pipeline.models import ComparablePair

    base: dict[str, Any] = dict(
        itinerary_a=a,
        itinerary_b=b,
        travel_diff_min=20,
        dep_diff_min=45,
        rate_diff=0.2,
        scenarios_compared=26,
        settings_compared=9,
        shared_days=250,
        ci_low=0.12,
        ci_high=0.28,
        assumption_sensitive=False,
        showcase=True,
    )
    base.update(kw)
    return ComparablePair(**base)


def test_sensitivity_section_lists_every_scenario_and_sensitive_pairs() -> None:
    from flight_pipeline.report import sensitivity_section

    rows = [
        {
            "scenario_id": "mct30_cut15_rec60",
            "is_default": True,
            "itineraries": 40,
            "min_connection_min": 30,
            "boarding_cutoff_min": 15,
            "recurrence_threshold": 0.6,
            "sufficient": 30,
            "median_rate": 0.81,
            "reversals": 0,
        },
        {
            "scenario_id": "mct45_cut20_rec75",
            "is_default": False,
            "itineraries": 31,
            "min_connection_min": 45,
            "boarding_cutoff_min": 20,
            "recurrence_threshold": 0.75,
            "sufficient": 22,
            "median_rate": None,
            "reversals": 2,
        },
    ]
    text = sensitivity_section(rows, [pair("x", "y", assumption_sensitive=True, showcase=False)], 5)
    assert "| mct30_cut15_rec60 (default) | 30 | 15 | 60% | 40 | 30 | 81% | 0 |" in text
    assert "| mct45_cut20_rec75 | 45 | 20 | 75% | 31 | 22 | n/a | 2 |" in text
    assert "x vs y" in text
    assert "5 pair-scenario combinations" in text


def finding(examples: list[Any], met: tuple[bool, bool]) -> Any:
    import datetime as dt

    from flight_pipeline.models import Finding, HubSelection
    from flight_pipeline.report import CI_METHOD, LIMITATIONS

    return Finding(
        ontime_period_start=dt.date(2025, 10, 1),
        ontime_period_end=dt.date(2026, 9, 30),
        t100_period_start=dt.date(2025, 9, 1),
        t100_period_end=dt.date(2026, 8, 31),
        db1b_quarters=["2025-4", "2026-1", "2026-2", "2026-3"],
        db1b_unknown_airline_share=0.0312,
        db1b_unmapped_airlines={"SY": 1400, "LF": 1200},
        db1b_unmapped_airline_share=0.0068,
        showcase_breakdown=None,
        airline_coverage=coverage_rows(),
        od_exclusions=exclusion_rows(),
        hubs=[HubSelection(airport="ORD", selected=True, reason="score")],
        unmet_constraints=[],
        od_pairs=od_rows()[:2],
        od_pairs_without_itineraries=[],
        default_results=[result_row("CMH-ORD-SAN:AA1+AA2", 300, 240)],
        showcase_examples=examples,
        criterion_min_examples_met=met[0],
        criterion_min_hubs_met=met[1],
        decision="go" if all(met) else "no_go",
        ci_method=CI_METHOD,
        limitations=list(LIMITATIONS),
        data_quality={"duplicate": 0, "invalid_schedule": 19},
    )


def test_limitations_cover_fr032() -> None:
    from flight_pipeline.report import LIMITATIONS

    text = " ".join(LIMITATIONS).lower()
    for phrase in (
        "hold",
        "gate change",
        "how full",
        "transfer time",
        "historical",
        "not a prediction",
    ):
        assert phrase in text, phrase


def test_showcase_section_shows_rates_with_sample_sizes_and_interval() -> None:
    from flight_pipeline.report import showcase_section

    results = {
        "CMH-ORD-SAN:AA1+AA2": result_row("CMH-ORD-SAN:AA1+AA2", 300, 270),
        "CMH-DFW-SAN:AA3+AA4": result_row("CMH-DFW-SAN:AA3+AA4", 290, 203),
    }
    text = showcase_section(
        [pair("CMH-ORD-SAN:AA1+AA2", "CMH-DFW-SAN:AA3+AA4")],
        results,
        {"CMH-ORD-SAN:AA1+AA2": "ORD", "CMH-DFW-SAN:AA3+AA4": "DFW"},
        0.95,
    )
    assert "90% (270 of 300 days)" in text
    assert "70% (203 of 290 days)" in text
    assert "+20 points (95% CI +12 to +28)" in text
    assert "1 showcase examples in 1 origin/destination pairs" in text
    assert "travel time within 20 min, departure within 45 min" in text


def test_summary_states_criteria_decision_and_attribution() -> None:
    from flight_pipeline.report import render_summary

    same_hub = [pair("CMH-ORD-SAN:AA1+AA2", "CMH-ORD-SAN:AA5+AA6")] * 3
    text = render_summary(finding(same_hub, (True, False)), ["## Extra section"])
    assert "**Decision: NO-GO**" in text
    assert "| At least 3 showcase examples | 3 | met |" in text
    assert "| Examples across at least 2 hubs | 1 | not met |" in text
    assert "## Extra section" in text
    assert "Bureau of Transportation Statistics" in text
    assert "airportsdata" in text
    assert "MIT" in text
    assert "paired day-level bootstrap" in text.lower()
    two_hubs = [*same_hub[:2], pair("CMH-DFW-SAN:AA3+AA4", "CMH-ORD-SAN:AA1+AA2")]
    text = render_summary(finding(two_hubs, (True, True)), [])
    assert "**Decision: GO**" in text
    assert "| Examples across at least 2 hubs | 2 | met |" in text


def test_summary_json_round_trips_through_finding_model() -> None:
    from flight_pipeline.models import Finding
    from flight_pipeline.report import finding_json

    f = finding([pair("a", "b")], (False, False))
    data = json.loads(finding_json(f))
    assert Finding.model_validate(data) == f
    assert finding_json(f) == finding_json(Finding.model_validate(data))  # stable bytes


def test_showcase_section_shows_strongest_example_per_pair_and_total() -> None:
    from flight_pipeline.report import showcase_section

    ids = [
        "CMH-ORD-SAN:AA1+AA2",
        "CMH-DFW-SAN:AA3+AA4",
        "CMH-ATL-SAN:DL5+DL6",
        "BOI-DEN-SEA:UA1+UA2",
        "BOI-SLC-SEA:DL7+DL8",
    ]
    results = {i: result_row(i, 300, 240) for i in ids}
    hub_of = {i: i.split("-")[1] for i in ids}
    examples = [
        pair(ids[0], ids[1], rate_diff=0.15),
        pair(ids[0], ids[2], rate_diff=0.25),
        pair(ids[3], ids[4], rate_diff=0.12),
    ]
    text = showcase_section(examples, results, hub_of, 0.95)
    assert "3 showcase examples in 2 origin/destination pairs, across 5 hubs" in text
    assert "+25 points" in text
    assert "+15 points" not in text  # weaker example for the same pair is only in summary.json
    assert "+12 points" in text
    assert "summary.json" in text


def test_data_quality_line_separates_exclusions_from_failures() -> None:
    from flight_pipeline.report import render_summary

    f = finding([], (False, False)).model_copy(
        update={
            "data_quality": {"cancelled": 10, "diverted": 2, "duplicate": 1, "invalid_schedule": 19}
        }
    )
    text = render_summary(f, [])
    assert "Excluded from every sample: duplicate: 1, invalid_schedule: 19." in text
    assert "Kept and counted as failures: cancelled: 10, diverted: 2." in text


def test_showcase_section_discloses_settings_compared_and_tight_layovers() -> None:
    from flight_pipeline.report import showcase_section

    ids = [
        "CMH-ORD-SAN:AA1+AA2",
        "CMH-DFW-SAN:AA3+AA4",
        "BOI-DEN-SEA:UA1+UA2",
        "BOI-SLC-SEA:DL7+DL8",
    ]
    results = {i: result_row(i, 300, 240) for i in ids}
    hub_of = {i: i.split("-")[1] for i in ids}
    examples = [
        pair(ids[0], ids[1], settings_compared=9),
        pair(ids[2], ids[3], settings_compared=6),
    ]
    layover = {ids[0]: 90, ids[1]: 31, ids[2]: 75, ids[3]: 60}
    sold = {ids[0]: 117, ids[1]: 45, ids[2]: 60, ids[3]: 31}
    text = showcase_section(
        examples,
        results,
        hub_of,
        0.95,
        layover=layover,
        tight={ids[1]},
        total_settings=9,
        sold=sold,
        routing_itineraries={ids[0]: 36, ids[1]: 2, ids[2]: 1, ids[3]: 1},
    )
    assert "1 of 2 examples were compared at all 9 settings" in text
    assert "fewest: 6" in text
    assert "90 / 31 (tighter than threshold)" in text
    assert "In 1 of 2 examples the lower itinerary's scheduled layover is shorter" in text
    assert "| 117 on 36 itineraries / 45 on 2 itineraries |" in text
    assert "Sold passengers on routing A / B" in text
    assert "| 9 of 9 | 250 |" in text


def exclusion_rows() -> list[Any]:
    from flight_pipeline.models import OdExclusions

    return [
        OdExclusions(
            origin="CMH",
            dest="SAN",
            candidates=40,
            excluded_layover=25,
            excluded_unsold=9,
            excluded_recurrence=2,
            qualifying=4,
        )
    ]


def test_exclusions_section_counts_each_rule_per_pair() -> None:
    from flight_pipeline.report import exclusions_section

    text = exclusions_section(exclusion_rows(), min_sold_passengers=30, recurrence_threshold=0.6)
    assert "| CMH-SAN | 40 | 25 | 9 | 2 | 4 |" in text
    assert "at least 30 sampled passengers" in text
    assert "60% of days" in text


def test_summary_states_single_period_db1b_quarters_and_sample_note() -> None:
    from flight_pipeline.report import render_summary

    text = render_summary(finding([], (False, False)), [])
    assert "DB1B quarters 2025-4 to 2026-3" in text
    assert "10% sample" in text
    assert "3.1%" in text  # passengers with an unrecorded selling airline
    assert "fares" in text.lower()


def test_hub_section_shows_seasonal_weather_shares() -> None:
    text = hub_report()
    assert "Weather by season (W / Sp / Su / Au)" in text
    # fixture: ORD peaks in summer with share 0.05 * 2; other seasons unknown
    line = next(line for line in text.splitlines() if "| ORD |" in line)
    assert "n/a / n/a / 10.0% / n/a" in line


def test_summary_reports_unmapped_selling_airlines() -> None:
    from flight_pipeline.report import render_summary

    text = render_summary(finding([], (False, False)), [])
    assert "0.7% of the sampled one-connection passengers" in text
    assert "SY 1,400, LF 1,200" in text


def test_missing_settings_described_per_showcase() -> None:
    from flight_pipeline.report import describe_missing_settings

    mcts, cutoffs = [20, 30, 45], [10, 15, 20]
    assert describe_missing_settings([], mcts, cutoffs) == ""
    assert (
        describe_missing_settings([(45, 10), (45, 15), (45, 20)], mcts, cutoffs)
        == "not at minimum connection 45 min"
    )
    assert describe_missing_settings([(45, 20), (20, 10)], mcts, cutoffs) == (
        "not at minimum connection / cutoff 20/10, 45/20"
    )


def test_showcase_section_names_missing_settings() -> None:
    from flight_pipeline.report import showcase_section

    a, b = "CMH-ORD-SAN:AA1+AA2", "CMH-DFW-SAN:AA3+AA4"
    results = {i: result_row(i, 300, 240) for i in (a, b)}
    text = showcase_section(
        [pair(a, b, settings_compared=6)],
        results,
        {a: "ORD", b: "DFW"},
        0.95,
        missing_settings={(a, b): "not at minimum connection 45 min"},
    )
    assert "6 of 9 (not at minimum connection 45 min)" in text
    assert "1 not at minimum connection 45 min" in text


def breakdown_inputs() -> tuple[list[Any], dict[str, Any]]:
    from flight_pipeline.models import Itinerary, PatternKey

    def it(iid: str, travel: int) -> Itinerary:
        od, legs = iid.split(":")
        o, h, d = od.split("-")
        l1, l2 = legs.split("+")
        return Itinerary(
            itinerary_id=iid,
            origin=o,
            hub=h,
            dest=d,
            inbound=PatternKey(
                marketing_airline=l1[:2], flight_number=int(l1[2:]), origin=o, dest=h
            ),
            outbound=PatternKey(
                marketing_airline=l2[:2], flight_number=int(l2[2:]), origin=h, dest=d
            ),
            partner_connection=l1[:2] != l2[:2],
            median_layover_min=60,
            median_travel_min=travel,
            median_dep_local_min=480,
            connect_share=1.0,
            sold_passengers=40,
        )

    ids = {
        "CMH-ORD-SAN:AA1+AA2": 300,
        "CMH-DFW-SAN:AA3+AA4": 320,
        "CMH-ORD-SAN:AA5+AA6": 280,
        "BOI-DEN-SEA:UA1+UA2": 200,
        "BOI-DEN-SEA:UA3+UA4": 210,
    }
    its = {i: it(i, t) for i, t in ids.items()}
    examples = [
        pair("CMH-ORD-SAN:AA1+AA2", "CMH-DFW-SAN:AA3+AA4"),  # cross-hub, 320 / 200 = 1.6
        pair("CMH-ORD-SAN:AA5+AA6", "CMH-ORD-SAN:AA1+AA2"),  # same hub, lower is tight
        pair("BOI-DEN-SEA:UA1+UA2", "BOI-DEN-SEA:UA3+UA4"),  # no nonstop
    ]
    return examples, its


def test_showcase_breakdown_counts_subsets() -> None:
    from flight_pipeline.report import showcase_breakdown

    examples, its = breakdown_inputs()
    b = showcase_breakdown(
        examples, its, tight={"CMH-ORD-SAN:AA1+AA2"}, nonstop_min={("CMH", "SAN"): 200}
    )
    assert b.examples == 3
    assert b.examples_per_pair == {"CMH-SAN": 2, "BOI-SEA": 1}
    assert b.cross_hub_examples == 1
    assert b.examples_without_tight_layover == 2
    assert b.pairs_without_tight_layover == 2
    assert b.hubs_without_tight_layover == ["DEN", "DFW", "ORD"]
    assert b.examples_without_nonstop == 1
    assert b.examples_slower_than_ratio == 1  # 320 / 200 > 1.5; 300 / 200 is not
    assert b.max_nonstop_ratio == 1.6


def test_breakdown_section_states_each_subset() -> None:
    from flight_pipeline.report import breakdown_section, showcase_breakdown

    examples, its = breakdown_inputs()
    b = showcase_breakdown(
        examples, its, tight={"CMH-ORD-SAN:AA1+AA2"}, nonstop_min={("CMH", "SAN"): 200}
    )
    text = breakdown_section(b)
    assert "| CMH-SAN | 2 |" in text
    assert "1 of 3 examples compare itineraries through different hubs" in text
    assert "2 examples, in 2 pairs and across 3 hubs (DEN, DFW, ORD)" in text
    assert "1 of 3 examples" in text
    assert "1.5 times" in text
    assert "1 example has no nonstop" in text


def coverage_rows() -> list[Any]:
    from flight_pipeline.models import AirlineCoverage

    return [
        AirlineCoverage(airline="DL", itineraries=350, sold_passengers=90000),
        AirlineCoverage(airline="WN", itineraries=0, sold_passengers=70000),
    ]


def test_airline_section_names_airlines_without_itineraries() -> None:
    from flight_pipeline.report import airline_section

    text = airline_section(coverage_rows(), recurrence_threshold=0.6)
    assert "| DL | 350 | 90,000 |" in text
    assert "| WN | 0 | 70,000 |" in text
    assert "**No itineraries:** WN" in text
    assert "flight number" in text


def test_airline_coverage_counts_itineraries_and_sold_passengers() -> None:
    from flight_pipeline.report import airline_coverage

    rows = airline_coverage(
        itinerary_airlines=["DL", "DL", "AA"],
        sold_same_airline={"DL": 500, "WN": 300, "AA": 40},
    )
    assert [(r.airline, r.itineraries, r.sold_passengers) for r in rows] == [
        ("DL", 2, 500),
        ("WN", 0, 300),
        ("AA", 1, 40),
    ]


def test_hub_section_states_configured_weights() -> None:
    from flight_pipeline.config import HubWeights

    assert "equally weighted" in hub_report()
    result = select_hubs(metrics(), hubs_cfg())
    text = hub_section(
        result.candidates,
        result.selection,
        result.unmet,
        result.median_weather_share,
        weights=HubWeights(airlines=2.0, departures=1.0, passengers=1.0),
    )
    assert "weights 2 (airlines), 1 (departures), 1 (passengers)" in text
    assert "equally weighted" not in text


def test_limitations_name_flight_number_identity() -> None:
    from flight_pipeline.report import LIMITATIONS

    assert any("flight number" in item for item in LIMITATIONS)


def test_routing_itineraries_counts_flight_pairs_per_routing() -> None:
    from flight_pipeline.report import routing_itineraries

    _, its = breakdown_inputs()
    counts = routing_itineraries(list(its.values()))
    assert counts["CMH-ORD-SAN:AA1+AA2"] == 2  # AA1+AA2 and AA5+AA6 share CMH-ORD-SAN AA:AA
    assert counts["CMH-DFW-SAN:AA3+AA4"] == 1
    assert counts["BOI-DEN-SEA:UA1+UA2"] == 2


def test_summary_includes_results_appendix_with_definition() -> None:
    from flight_pipeline.report import render_summary, results_section

    appendix = results_section(
        [result_row("CMH-ORD-SAN:AA1+AA2", 300, 240)], {"CMH-ORD-SAN:AA1+AA2": "ORD"}, 30
    )
    text = render_summary(finding([], (False, False)), ["## Section"], 3, 2, [appendix])
    assert "## Section" in text
    assert appendix.splitlines()[0] in text
    assert "connection feasibility" in text.lower()
    assert "Slack min / p10 / p50 / p90 (minutes)" in text
    assert text.index("## Section") < text.index(appendix.splitlines()[0])


def test_json_outputs_have_models() -> None:
    import pytest
    from pydantic import ValidationError

    from flight_pipeline.models import QualitySummary, ScenarioSummary

    with pytest.raises(ValidationError):
        QualitySummary.model_validate({"by_month": {}})
    with pytest.raises(ValidationError):
        ScenarioSummary.model_validate({"scenario_id": "x"})
