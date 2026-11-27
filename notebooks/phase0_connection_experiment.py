import marimo

__generated_with = "0.9.0"
app = marimo.App(width="medium")


@app.cell
def _():
    """Phase 0: BTS connection feasibility experiment.

    Reads only data/derived/phase0/ and reports/phase0/ (override with PHASE0_DERIVED and
    PHASE0_REPORTS). Every number comes from the pipeline's outputs; this notebook only
    formats and draws them.
    """
    import json
    import os
    from pathlib import Path

    import altair as alt
    import duckdb
    import marimo as mo

    _here = Path(__file__).resolve().parent
    derived = Path(os.environ.get("PHASE0_DERIVED", _here.parent / "data" / "derived" / "phase0"))
    reports = Path(os.environ.get("PHASE0_REPORTS", _here.parent / "reports" / "phase0"))
    _con = duckdb.connect()

    def rows(name: str) -> list[dict]:
        """All rows of one derived Parquet table, as dicts."""
        _cur = _con.execute(f"SELECT * FROM read_parquet('{(derived / name).as_posix()}')")
        _cols = [d[0] for d in _cur.description]
        return [dict(zip(_cols, _r, strict=True)) for _r in _cur.fetchall()]

    finding = json.loads((reports / "summary.json").read_text(encoding="utf-8"))
    return alt, derived, finding, json, mo, rows


@app.cell
def _(finding, mo):
    _decision = {"go": "GO", "no_go": "NO-GO", "pivot": "PIVOT"}[finding["decision"]]
    mo.md(
        f"""
        # Phase 0: connection feasibility experiment

        Data period {finding["ontime_period_start"]} to {finding["ontime_period_end"]} for
        on-time flights, T-100 passengers and DB1B sold routings (quarters
        {", ".join(finding["db1b_quarters"])}). DB1B is a 10% ticket sample;
        {finding["db1b_unknown_airline_share"] * 100:.1f}% of its one-connection passengers
        had a leg with no recorded selling airline and were not counted.

        **Decision: {_decision}** ({len(finding["showcase_examples"])} showcase examples).
        Connection feasibility is a historical frequency, not a prediction.
        """
    )
    return


@app.cell
def _(mo, rows):
    _selection = {_s["airport"]: _s for _s in rows("hub_selection.parquet")}
    _table = [
        {
            "Rank": _c["rank"],
            "Airport": _c["airport"],
            "Score": round(_c["score"], 3),
            "Eligible": "yes" if _c["eligible"] else "no",
            "Departures": _c["departures"],
            "Airlines": ", ".join(_c["airlines"]),
            "Passengers": "missing" if _c["passengers"] is None else _c["passengers"],
            "Weather share": f"{_c['weather_share'] * 100:.1f}%",
            "Weather peak": _c["weather_peak_season"],
            "Selected": _selection[_c["airport"]]["reason"] or "",
        }
        for _c in sorted(rows("hub_candidates.parquet"), key=lambda _c: _c["rank"])
    ]
    mo.vstack([mo.md("## Hub selection"), mo.ui.table(_table, selection=None)])
    return


@app.cell
def _(finding, mo):
    _excl = [
        {
            "Pair": f"{_e['origin']}-{_e['dest']}",
            "Candidates": _e["candidates"],
            "Times can never connect": _e["excluded_bounds"],
            "Routing not sold": _e["excluded_unsold"],
            "Never connect within limits": _e["excluded_not_connecting"],
            "Connect on too few days": _e["excluded_recurrence"],
            "Qualifying": _e["qualifying"],
        }
        for _e in finding["od_exclusions"]
    ]
    mo.vstack(
        [
            mo.md(
                "## Itinerary rules applied\n\n"
                "Candidates removed by each rule, in order, for every selected pair."
            ),
            mo.ui.table(_excl, selection=None),
        ]
    )
    return


@app.cell
def _(finding, mo, rows):
    _itin = {_i["itinerary_id"]: _i for _i in rows("itineraries.parquet")}

    def _rate(_r: dict) -> str:
        if _r["feasibility_rate"] is None:
            return f"insufficient data ({_r['paired_days']} days)"
        return (
            f"{_r['feasibility_rate'] * 100:.0f}% "
            f"({_r['count_feasible']} of {_r['paired_days']} days)"
        )

    _results = [
        {
            "Itinerary": _r["itinerary_id"],
            "Connection feasibility": _rate(_r),
            "Sold passengers (DB1B sample)": _itin[_r["itinerary_id"]]["sold_passengers"],
            "Days the flights connect": (
                f"{_itin[_r['itinerary_id']]['connect_share'] * 100:.0f}%"
            ),
            "Cancelled": _r["count_cancelled"],
            "Diverted": _r["count_diverted"],
            "Slack p10 / p50 / p90 (min)": (
                f"{_r['slack_p10']} / {_r['slack_p50']} / {_r['slack_p90']}"
            ),
        }
        for _r in finding["default_results"]
    ]
    mo.vstack(
        [
            mo.md(
                "## Connection feasibility by itinerary (default assumptions)\n\n"
                "Every rate is shown with its number of paired days."
            ),
            mo.ui.table(_results, selection=None),
        ]
    )
    return


@app.cell
def _(alt, finding, mo):
    _by_id = {_r["itinerary_id"]: _r for _r in finding["default_results"]}
    _best: dict = {}
    for _p in finding["showcase_examples"]:
        _od = _p["itinerary_a"].split(":")[0].split("-")
        _key = f"{_od[0]}-{_od[2]}"
        if _key not in _best or _p["rate_diff"] > _best[_key]["rate_diff"]:
            _best[_key] = _p
    _rows = []
    for _p in sorted(_best.values(), key=lambda _x: -_x["rate_diff"])[:6]:
        for _side, _role in (("itinerary_a", "higher"), ("itinerary_b", "lower")):
            _r = _by_id[_p[_side]]
            _rows.append(
                {
                    "itinerary": _r["itinerary_id"],
                    "p10": _r["slack_p10"],
                    "p50": _r["slack_p50"],
                    "p90": _r["slack_p90"],
                    "label": f"{_r['feasibility_rate'] * 100:.0f}% of {_r['paired_days']} days",
                    "role": f"{_role} connection feasibility",
                }
            )
    if _rows:
        _base = alt.Chart(alt.Data(values=_rows)).encode(
            y=alt.Y("itinerary:N", sort=None, title=None)
        )
        _chart = (
            _base.mark_rule(strokeWidth=3).encode(
                x=alt.X("p10:Q", title="Raw slack, minutes (p10 to p90; tick = median)"),
                x2="p90:Q",
                color=alt.Color("role:N", title=None),
                strokeDash=alt.StrokeDash("role:N", title=None),
            )
            + _base.mark_tick(thickness=3, size=14, color="black").encode(x="p50:Q")
            + _base.mark_text(align="left", dx=6).encode(x="p90:Q", text="label:N")
        ).properties(width=520)
        _pairs = [
            {
                "Higher": _p["itinerary_a"],
                "Lower": _p["itinerary_b"],
                "Difference (points)": round(_p["rate_diff"] * 100),
                "Settings compared": _p["settings_compared"],
                "Shared dates": _p["shared_days"],
            }
            for _p in sorted(_best.values(), key=lambda _x: -_x["rate_diff"])
        ]
        _out = mo.vstack(
            [
                mo.md(
                    "## Slack for the strongest showcase pairs\n\n"
                    "Line style and colour both mark the itinerary with the higher connection "
                    "feasibility; the label gives its rate and sample size."
                ),
                mo.ui.altair_chart(_chart),
                mo.md(
                    "Settings compared: distinct (minimum connection time, boarding cutoff) "
                    "settings at which both itineraries had sufficient data, so their order "
                    "could be checked."
                ),
                mo.ui.table(_pairs, selection=None),
            ]
        )
    else:
        _out = mo.md("## Showcase examples\n\nNo pair met every showcase condition.")
    _out
    return


@app.cell
def _(alt, derived, json, mo):
    _scen = json.loads((derived / "sensitivity_summary.json").read_text(encoding="utf-8"))
    for _s in _scen:
        _s["median_label"] = (
            "n/a" if _s["median_rate"] is None else f"{_s['median_rate'] * 100:.0f}%"
        )
    _bars = alt.Chart(alt.Data(values=_scen)).encode(
        y=alt.Y("scenario_id:N", sort=None, title="Scenario"),
        x=alt.X(
            "median_rate:Q",
            title="Median connection feasibility",
            scale=alt.Scale(domain=[0, 1]),
        ),
    )
    _chart = (
        _bars.mark_bar() + _bars.mark_text(align="left", dx=4).encode(text="median_label:N")
    ).properties(width=480)
    mo.vstack(
        [
            mo.md(
                "## Sensitivity to assumptions\n\n"
                "Median connection feasibility among itineraries with sufficient data, per "
                "scenario (minimum connection time, boarding cutoff, recurrence threshold), "
                "and the number of comparable pairs whose order reversed."
            ),
            mo.ui.altair_chart(_chart),
            mo.ui.table(_scen, selection=None),
        ]
    )
    return


if __name__ == "__main__":
    app.run()
