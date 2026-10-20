"""Tests for rig_comm.core.evaluate: score fields, the block/emit decision,
banned-phrase blocking, and decision flips from custom rules and thresholds."""
from __future__ import annotations

from rig_comm import evaluate, validate_rules
from rig_comm.gates import GateEngine, compute_entropy_ratio, compute_reactance_risk

GOOD_MESSAGE = """Sarah,

Your team is spending 40% of engineering hours on architecture maintenance.
At 200 engineers, that is 80 full-time equivalents not shipping product. The
cost lands on every roadmap slip.

The real number is probably worse. Architecture tax scales nonlinearly
with service count. Every new endpoint requires coordination across 4-7 services.
That is not maintenance. That is an architecture actively hostile to velocity.

If this is intentional, if you are betting the next round makes it
manageable, ignore this. But if the 40% is creeping toward 50%, the
math gets nonlinear fast.

I have a hypothesis about which 3 services are causing 80% of the
coupling. I would need 15 minutes with the dependency graph to confirm it.

Mike
"""

BLOCKED_MESSAGE = "Hope this finds you well. Would love to chat about your needs. Let me know your thoughts!"


def test_good_message_emits() -> None:
    report = evaluate(GOOD_MESSAGE, channel="email")
    assert report.can_ship is True
    assert report.blocks == []
    assert report.channel_formula == "email_voltage_score"
    assert report.comm_raw_score > 0.65
    assert 0.0 <= report.channel_score <= 1.0
    assert report.banned_phrases == []


def test_banned_phrase_blocks() -> None:
    report = evaluate(BLOCKED_MESSAGE, channel="email")
    assert report.can_ship is False
    assert any("BANNED_PHRASES" in b for b in report.blocks)
    assert "hope this finds you well" in report.banned_phrases


def test_report_to_dict_shape() -> None:
    d = evaluate(GOOD_MESSAGE).to_dict()
    for key in ("text", "channel", "comm_raw_score", "channel_score", "channel_formula",
                "phase_detection", "banned_phrases", "can_ship", "blocks", "warnings", "score"):
        assert key in d
    assert set(d["phase_detection"]) == {"wound", "mirror", "autonomy", "qualification", "open_loop"}


def test_custom_rule_blocks_a_phrase_defaults_allow() -> None:
    rules = validate_rules({"banned_phrases": ["per my last email"]})
    text = "Per my last email, the numbers are attached."
    assert GateEngine.scan_banned_phrases(text) == []
    report = evaluate(text, channel="email", rules=rules)
    assert report.can_ship is False
    assert report.banned_phrases == ["per my last email"]


def test_severity_off_disables_a_gate() -> None:
    rules = validate_rules({"severities": {"BANNED_PHRASES": "off"}})
    report = evaluate(BLOCKED_MESSAGE, channel="email", rules=rules)
    assert all("BANNED_PHRASES" not in b for b in report.blocks)


def test_threshold_change_flips_decision() -> None:
    strict = validate_rules({"thresholds": {"autonomy_min": 0.99}})
    report = evaluate(GOOD_MESSAGE, channel="email", rules=strict)
    assert report.can_ship is False
    assert any("AUTONOMY" in b for b in report.blocks)


def test_manipulation_markers_are_configurable() -> None:
    rules = validate_rules({"manipulation_markers": ["architecture"]})
    report = evaluate(GOOD_MESSAGE, channel="email", rules=rules)
    assert any("MANIPULATION_LANGUAGE" in b for b in report.blocks)


def test_reactance_markers_are_configurable() -> None:
    rules = validate_rules({"reactance_markers": ["hypothesis"], "thresholds": {"reactance_max": 0.05}})
    assert compute_reactance_risk(GOOD_MESSAGE, list(rules.reactance_markers)) > 0
    report = evaluate(GOOD_MESSAGE, channel="email", rules=rules)
    assert any("REACTANCE" in b for b in report.blocks)


def test_linkedin_channel_uses_linkedin_gates() -> None:
    report = evaluate(GOOD_MESSAGE, channel="linkedin")
    assert report.channel_formula == "bdf30"
    gate_names = [r.name for r in report.gate_report.all_results]
    assert "SWARM_DISAGREE" in gate_names
    assert "HOOK_WEAK" in gate_names


def test_entropy_ratio_and_reactance_helpers() -> None:
    assert compute_entropy_ratio(GOOD_MESSAGE, "generic baseline text repeated repeated") > 1.2
    assert compute_reactance_risk("You must act now! Hurry!") > 0.20
    assert compute_reactance_risk("Quiet, specific, and optional.") == 0.0


def test_over_explaining_warns_but_ships() -> None:
    rules = validate_rules({"thresholds": {"word_count_warn": 10}})
    report = evaluate(GOOD_MESSAGE, channel="email", rules=rules)
    assert any("OVER_EXPLAINING" in w for w in report.warnings)
    assert report.can_ship is True
