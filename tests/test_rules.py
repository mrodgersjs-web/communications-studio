"""Tests for the configurable rule set: loading, validation, and wiring."""
from __future__ import annotations

import json

import pytest

from rig_comm.rules import (
    DEFAULT_BANNED_PHRASES,
    DEFAULT_THRESHOLDS,
    GATE_SEVERITIES,
    RuleSet,
    RuleValidationError,
    default_rules,
    dump_rules,
    load_rules,
    validate_rules,
)


def test_default_rules_match_doctrine() -> None:
    rules = default_rules()
    assert rules.banned_phrases == DEFAULT_BANNED_PHRASES
    assert rules.thresholds == DEFAULT_THRESHOLDS
    assert rules.severities == GATE_SEVERITIES
    assert rules.threshold("autonomy_min") == 0.70
    assert rules.severity("BANNED_PHRASES") == "block"
    assert rules.severity("OVER_EXPLAINING") == "warn"


def test_validate_rules_accepts_partial_document() -> None:
    rules = validate_rules({"banned_phrases": ["circle back"]})
    assert rules.banned_phrases == ("circle back",)
    # Untouched sections keep doctrine defaults.
    assert rules.thresholds == DEFAULT_THRESHOLDS
    assert rules.reactance_markers == default_rules().reactance_markers


def test_validate_rules_rejects_unknown_top_level_key() -> None:
    with pytest.raises(RuleValidationError) as excinfo:
        validate_rules({"banned_phrases": [], "bananas": 3})
    assert "unknown key 'bananas'" in str(excinfo.value)


def test_validate_rules_rejects_bad_phrase_lists() -> None:
    with pytest.raises(RuleValidationError) as excinfo:
        validate_rules({"banned_phrases": "just checking in"})
    assert "must be a list of strings" in str(excinfo.value)

    with pytest.raises(RuleValidationError) as excinfo:
        validate_rules({"banned_phrases": ["ok", "", "ok"]})
    assert "non-empty string" in str(excinfo.value)
    assert "duplicates" in str(excinfo.value)


def test_validate_rules_rejects_unknown_and_out_of_range_thresholds() -> None:
    with pytest.raises(RuleValidationError) as excinfo:
        validate_rules({"thresholds": {"autonomy_min": 2.0, "banana_min": 1}})
    problems = str(excinfo.value)
    assert "outside valid range" in problems
    assert "not a known threshold" in problems


def test_validate_rules_rejects_non_numeric_threshold() -> None:
    with pytest.raises(RuleValidationError) as excinfo:
        validate_rules({"thresholds": {"cfas_min": "82"}})
    assert "must be a number" in str(excinfo.value)


def test_validate_rules_rejects_bad_severity() -> None:
    with pytest.raises(RuleValidationError) as excinfo:
        validate_rules({"severities": {"ENTROPY": "explode", "NOPE": "warn"}})
    problems = str(excinfo.value)
    assert "must be one of" in problems
    assert "not a known gate name" in problems


def test_validate_rules_maps_yaml_booleans_for_severities() -> None:
    # YAML reads a bare `off` as boolean False; it means the same thing here.
    rules = validate_rules({"severities": {"ENTROPY": False, "REACTANCE": True}})
    assert rules.severity("ENTROPY") == "off"
    assert rules.severity("REACTANCE") == "block"


def test_validate_rules_rejects_non_mapping_document() -> None:
    with pytest.raises(RuleValidationError):
        validate_rules(["banned_phrases"])


def test_load_rules_yaml_and_json_agree(tmp_path) -> None:
    doc = {
        "banned_phrases": ["circle back"],
        "thresholds": {"reactance_max": 0.5},
        "severities": {"ENTROPY": "off"},
    }
    json_path = tmp_path / "rules.json"
    json_path.write_text(json.dumps(doc), encoding="utf-8")

    yaml_path = tmp_path / "rules.yaml"
    yaml_path.write_text(
        "banned_phrases:\n  - circle back\nthresholds:\n  reactance_max: 0.5\n"
        "severities:\n  ENTROPY: off\n",
        encoding="utf-8",
    )

    from_json = load_rules(json_path)
    from_yaml = load_rules(yaml_path)
    assert from_json == from_yaml
    assert from_json.threshold("reactance_max") == 0.5
    assert from_json.severity("ENTROPY") == "off"


def test_load_rules_missing_file_and_wrong_extension(tmp_path) -> None:
    with pytest.raises(RuleValidationError) as excinfo:
        load_rules(tmp_path / "missing.yaml")
    assert "file not found" in str(excinfo.value)

    bad = tmp_path / "rules.toml"
    bad.write_text("x = 1", encoding="utf-8")
    with pytest.raises(RuleValidationError) as excinfo:
        load_rules(bad)
    assert "unsupported extension" in str(excinfo.value)


def test_load_rules_invalid_json_is_reported(tmp_path) -> None:
    bad = tmp_path / "rules.json"
    bad.write_text("{not json", encoding="utf-8")
    with pytest.raises(RuleValidationError) as excinfo:
        load_rules(bad)
    assert "not valid JSON" in str(excinfo.value)


def test_load_rules_invalid_yaml_is_reported(tmp_path) -> None:
    bad = tmp_path / "rules.yaml"
    bad.write_text("banned_phrases: [unterminated\n", encoding="utf-8")
    with pytest.raises(RuleValidationError) as excinfo:
        load_rules(bad)
    assert "not valid YAML" in str(excinfo.value)


def test_dump_rules_round_trips() -> None:
    rules = validate_rules({"thresholds": {"word_count_warn": 150}})
    assert validate_rules(json.loads(dump_rules(rules))) == rules


def test_rule_set_is_immutable() -> None:
    rules = RuleSet()
    with pytest.raises(Exception):
        rules.banned_phrases = ()  # type: ignore[misc]
