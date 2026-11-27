"""Config loading and validation (contracts/config.md)."""

import copy
import tomllib
from pathlib import Path
from typing import Any

import pytest

from flight_pipeline.config import Config, ConfigError, load_config, parse_config

REPO = Path(__file__).resolve().parents[3]
CONFIG_PATH = REPO / "config" / "phase1.toml"


def raw() -> dict[str, Any]:
    with CONFIG_PATH.open("rb") as f:
        return tomllib.load(f)


def mutated(section: str, key: str, value: Any) -> dict[str, Any]:
    data = copy.deepcopy(raw())
    target = data
    for part in section.split("."):
        target = target[part]
    target[key] = value
    return data


def test_committed_config_loads() -> None:
    cfg = load_config(CONFIG_PATH)
    assert isinstance(cfg, Config)
    assert cfg.seed == 20261124
    assert cfg.hubs.count == 7
    assert cfg.repo_root == REPO
    assert cfg.path(cfg.paths.raw_dir) == REPO / "data" / "raw"


def test_every_contract_section_present() -> None:
    assert set(raw()) == {
        "seed",
        "paths",
        "period",
        "sources",
        "timezones",
        "hubs",
        "itineraries",
        "feasibility",
        "selection",
        "comparison",
        "sensitivity",
        "quality",
        "runtime",
        "showcase",
        "insights",
        "notes",
    }


@pytest.mark.parametrize(
    ("section", "key", "value", "message"),
    [
        ("hubs", "count", 9, "hubs.count"),
        ("hubs", "count", 4, "hubs.count"),
        ("selection", "od_pairs_count", 16, "selection.od_pairs_count"),
        ("selection", "od_pairs_count", 9, "selection.od_pairs_count"),
        ("hubs", "airline_share_min", 1.5, "hubs.airline_share_min"),
        ("itineraries", "recurrence_threshold", -0.1, "itineraries.recurrence_threshold"),
        ("comparison", "ci_level", 1.0, "comparison.ci_level"),
        ("quality", "clock_mismatch_max_share", 2.0, "quality.clock_mismatch_max_share"),
        ("sensitivity", "min_connection_min", [20, 45, 60], "min_connection_min"),
        ("sensitivity", "boarding_cutoff_min", [10, 20, 25], "boarding_cutoff_min"),
        ("sensitivity", "recurrence_threshold", [0.5, 0.75, 0.9], "recurrence_threshold"),
        ("sensitivity", "boarding_cutoff_min", [15, 20], "at least 3"),
        ("period", "end", "2025-03", "12 months"),
        ("period", "start", "2024/07", "YYYY-MM"),
        ("itineraries", "min_sold_passengers", -1, "itineraries.min_sold_passengers"),
        ("itineraries", "carrier_map", {"US": "A"}, "carrier_map"),
        ("sources.db1b", "url_pattern", "https://example.org/{year}.zip", "quarter"),
        ("sources.db1b", "checksums", {"2024-5": "0" * 64}, "YYYY-Q"),
        ("hubs", "spring_months", [3, 4], "each month"),
        ("hubs", "autumn_months", [9, 10, 11, 12], "each month"),
        ("sources.ontime", "url_pattern", "https://example.org/{year}.zip", "month"),
        ("itineraries", "partners", [["AA"]], "partners"),
        ("hubs", "weights", {"airlines": 0.0, "departures": 0.0, "passengers": 0.0}, "weights"),
    ],
)
def test_validation_rules(section: str, key: str, value: Any, message: str) -> None:
    with pytest.raises(ConfigError, match=message):
        parse_config(mutated(section, key, value), REPO)


def test_unknown_key_rejected() -> None:
    with pytest.raises(ConfigError, match=r"hubs\.colour"):
        parse_config(mutated("hubs", "colour", "blue"), REPO)


def test_missing_key_rejected() -> None:
    data = raw()
    del data["feasibility"]["min_sample_days"]
    with pytest.raises(ConfigError, match=r"feasibility\.min_sample_days"):
        parse_config(data, REPO)


def test_timezone_override_must_be_valid_iana() -> None:
    data = mutated("timezones", "overrides", {"XYZ": {"tz": "Mars/Base", "source": "test"}})
    with pytest.raises(ConfigError, match="Mars/Base"):
        parse_config(data, REPO)


def test_timezone_override_accepted() -> None:
    data = mutated(
        "timezones", "overrides", {"XYZ": {"tz": "America/Denver", "source": "FAA chart"}}
    )
    cfg = parse_config(data, REPO)
    assert cfg.timezones.overrides["XYZ"].tz == "America/Denver"


def test_period_helpers() -> None:
    cfg = load_config(CONFIG_PATH)
    months = cfg.period.months()
    assert months[0] == (2024, 7)
    assert months[-1] == (2025, 6)
    assert len(months) == 12
    start, end = cfg.period.dates()
    assert str(start) == "2024-07-01"
    assert str(end) == "2025-06-30"
    assert cfg.period.days() == 365
    assert cfg.period.quarters() == [(2024, 3), (2024, 4), (2025, 1), (2025, 2)]


@pytest.mark.parametrize(("start", "end"), [("2024-08", "2025-07"), ("2024-02", "2025-01")])
def test_period_must_be_whole_quarters(start: str, end: str) -> None:
    data = mutated("period", "start", start)
    data["period"]["end"] = end
    with pytest.raises(ConfigError, match="quarter"):
        parse_config(data, REPO)


def test_period_has_one_start_and_end() -> None:
    assert set(raw()["period"]) == {"start", "end"}


def test_db1b_source_and_sold_routing_rules() -> None:
    cfg = load_config(CONFIG_PATH)
    assert "{year}" in cfg.sources.db1b.url_pattern
    assert "{quarter}" in cfg.sources.db1b.url_pattern
    assert cfg.itineraries.min_sold_passengers == 30
    assert cfg.itineraries.carrier_map == {}
    data = mutated("itineraries", "carrier_map", {"US": "AA"})
    assert parse_config(data, REPO).itineraries.carrier_map == {"US": "AA"}


def test_db1b_checksum_keys_are_quarters() -> None:
    data = mutated("sources.db1b", "checksums", {"2024-3": "a" * 64})
    assert parse_config(data, REPO).sources.db1b.checksums == {"2024-3": "a" * 64}


def test_season_of_month() -> None:
    cfg = load_config(CONFIG_PATH)
    assert cfg.hubs.season_of(1) == "winter"
    assert cfg.hubs.season_of(4) == "spring"
    assert cfg.hubs.season_of(7) == "summer"
    assert cfg.hubs.season_of(10) == "autumn"


def test_min_connection_for_hub() -> None:
    data = mutated("itineraries", "min_connection_by_hub", {"ORD": 50})
    cfg = parse_config(data, REPO)
    assert cfg.itineraries.min_connection_for("ORD", partner=False) == 50
    assert cfg.itineraries.min_connection_for("DEN", partner=False) == 30
    assert cfg.itineraries.min_connection_for("DEN", partner=True) == 45
    assert cfg.itineraries.min_connection_for("ORD", partner=True) == 50
