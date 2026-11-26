"""Phase 1 configuration: new keys and rules (specs/002 contracts/config.md)."""

import copy
import datetime as dt
import tomllib
from pathlib import Path
from typing import Any

import pytest

from flight_pipeline.config import ConfigError, load_config, load_disruption_notes, parse_config

REPO = Path(__file__).resolve().parents[3]
CONFIG_PATH = REPO / "config" / "phase1.toml"
NOTES_PATH = REPO / "config" / "disruption_notes.toml"


def raw() -> dict[str, Any]:
    with CONFIG_PATH.open("rb") as f:
        return tomllib.load(f)


def mutated(section: str, key: str, value: Any) -> dict[str, Any]:
    data = copy.deepcopy(raw())
    data[section][key] = value
    return data


def test_committed_phase1_config_loads() -> None:
    cfg = load_config(CONFIG_PATH)
    assert cfg.itineraries.identity == "schedule"
    assert cfg.itineraries.slot_window_min == 30
    assert cfg.showcase.routes_min == 8
    assert cfg.showcase.routes_max == 12
    assert cfg.showcase.landing_budget_kb == 150
    assert cfg.insights.faster_margin == 0.02
    assert cfg.insights.buffer_share == 0.95
    assert cfg.insights.monthly_min_sample == 20
    assert cfg.path(cfg.notes.disruption_file) == NOTES_PATH


@pytest.mark.parametrize("section", ["showcase", "insights", "notes"])
def test_new_sections_required(section: str) -> None:
    data = raw()
    del data[section]
    with pytest.raises(ConfigError, match=section):
        parse_config(data, REPO)


@pytest.mark.parametrize(
    ("section", "key", "value", "message"),
    [
        ("itineraries", "slot_window_min", 9, "slot_window_min"),
        ("itineraries", "slot_window_min", 91, "slot_window_min"),
        ("itineraries", "identity", "flight_number", "identity"),
        ("showcase", "routes_min", 13, "routes_min"),
        ("showcase", "max_share_route", 0.0, "max_share_route"),
        ("showcase", "max_share_hub", 1.5, "max_share_hub"),
        ("showcase", "cross_hub_share_min", -0.1, "cross_hub_share_min"),
        ("showcase", "size_budget_kb", 0, "size_budget_kb"),
        ("insights", "faster_margin", 0.25, "faster_margin"),
        ("insights", "buffer_share", 0.5, "buffer_share"),
        ("insights", "buffer_share", 1.0, "buffer_share"),
        ("insights", "monthly_min_sample", 0, "monthly_min_sample"),
    ],
)
def test_validation_rules(section: str, key: str, value: Any, message: str) -> None:
    with pytest.raises(ConfigError, match=message):
        parse_config(mutated(section, key, value), REPO)


def test_unknown_key_in_new_section_rejected() -> None:
    with pytest.raises(ConfigError, match=r"showcase\.colour"):
        parse_config(mutated("showcase", "colour", "blue"), REPO)


def test_committed_disruption_notes_load() -> None:
    cfg = load_config(CONFIG_PATH)
    notes = load_disruption_notes(NOTES_PATH, cfg.period.dates())
    ids = [n.note_id for n in notes]
    assert "crowdstrike-2024-07" in ids
    assert [(n.start, n.note_id) for n in notes] == sorted((n.start, n.note_id) for n in notes)
    assert all(n.source_url.startswith("https://") for n in notes)


def write_notes(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "notes.toml"
    path.write_text(body, encoding="utf-8")
    return path


PERIOD = (dt.date(2024, 7, 1), dt.date(2025, 6, 30))
GOOD = """
[[note]]
id = "x"
start = "2024-08-01"
end = "2024-08-02"
airlines = ["DL"]
airports = []
text = "An event."
source = "https://example.gov/x"
"""


def test_valid_note_parsed(tmp_path: Path) -> None:
    [note] = load_disruption_notes(write_notes(tmp_path, GOOD), PERIOD)
    assert note.note_id == "x"
    assert note.start == dt.date(2024, 8, 1)
    assert note.airlines == ["DL"]


@pytest.mark.parametrize(
    ("old", "new", "message"),
    [
        ('start = "2024-08-01"', 'start = "2024-06-01"', "period"),
        ('end = "2024-08-02"', 'end = "2024-07-30"', "end"),
        ('airlines = ["DL"]', "airlines = []", "airline or airport"),
        ('text = "An event."', 'text = ""', "text"),
        ('source = "https://example.gov/x"', 'source = "http://example.gov/x"', "https"),
        ('source = "https://example.gov/x"', "", "source"),
        ("airports = []", 'airprots = ["EWR"]', "unknown keys"),
        ('id = "x"', 'id = " "', "id is empty"),
        ('id = "x"', "", "id"),
    ],
)
def test_invalid_notes_rejected(tmp_path: Path, old: str, new: str, message: str) -> None:
    with pytest.raises(ConfigError, match=message):
        load_disruption_notes(write_notes(tmp_path, GOOD.replace(old, new)), PERIOD)


def test_duplicate_note_ids_rejected(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="duplicate"):
        load_disruption_notes(write_notes(tmp_path, GOOD + GOOD), PERIOD)
