"""Tests for the formula registry, the legacy scoring engine, and doctrine checks."""
from __future__ import annotations

from dataclasses import fields

from rig_comm.doctrine import FORMULA_WEIGHTS, validate_doctrine
from rig_comm.formulas import (
    IDPScoreInput,
    bdf30,
    catchphrase_potential,
    catchphrase_score,
    comm_raw_score,
    compute_idp,
    craft_coefficient,
    customer_facing_artifact_score,
    email_reply_score,
    email_voltage_score,
    falsifiable_bet_strength,
    format_novelty,
    idp_classify,
    memory_compounding_score,
    orthodoxy_destruction_depth,
    proof_availability,
    rpe,
    semantic_inversion_novelty,
    villain_class_specificity,
    wound_resonance,
)
from rig_comm.scoring import CommunicationScore, GateEngine, example_sarah_chen

IDP_COMPONENTS = [
    orthodoxy_destruction_depth,
    villain_class_specificity,
    falsifiable_bet_strength,
    semantic_inversion_novelty,
    wound_resonance,
    format_novelty,
    catchphrase_potential,
    proof_availability,
    memory_compounding_score,
]


def _full_score() -> CommunicationScore:
    return CommunicationScore(**{f.name: 1.0 for f in fields(CommunicationScore)})


def test_idp_components_respect_ranges() -> None:
    zero = IDPScoreInput()
    full = IDPScoreInput(**{f.name: 1.0 for f in fields(IDPScoreInput)})
    for fn in IDP_COMPONENTS:
        low, high = fn(zero), fn(full)
        assert 0.0 <= low <= high <= 1.0, fn.__name__


def test_compute_idp_and_classify() -> None:
    zero = IDPScoreInput()
    full = IDPScoreInput(**{f.name: 1.0 for f in fields(IDPScoreInput)})
    assert compute_idp(zero) < compute_idp(full)
    assert 0.0 <= compute_idp(full) <= 1.0

    assert idp_classify(0.95).startswith("Elite")
    assert idp_classify(0.85).startswith("Exceptional")
    assert idp_classify(0.75).startswith("Strong")
    assert idp_classify(0.67).startswith("Marginal")
    assert idp_classify(0.55).startswith("Insufficient")
    assert idp_classify(0.20).startswith("Generic")


def test_channel_formulas_are_monotonic_and_bounded() -> None:
    zero, full = CommunicationScore(), _full_score()
    for fn in (comm_raw_score, email_voltage_score, email_reply_score, bdf30,
               customer_facing_artifact_score):
        low, high = fn(zero), fn(full)
        assert 0.0 <= low <= high <= 1.0, fn.__name__


def test_craft_catchphrase_and_rpe() -> None:
    zero, full = CommunicationScore(), _full_score()
    # craft_coefficient is a multiplier and rpe is a decayed residue sum;
    # neither is bounded to 0-1, so only ordering is asserted.
    assert craft_coefficient(full) > craft_coefficient(zero)
    assert 0.0 <= catchphrase_score(full) <= 1.0
    assert rpe(full, gamma=0.9) > rpe(zero, gamma=0.9)


def test_legacy_scoring_engine_methods() -> None:
    # scoring.CommunicationScore carries its own V10 method implementations;
    # exercise them without requiring byte-equality with the formulas registry.
    score = example_sarah_chen()
    assert score.wound_precision == 0.85
    assert 0.0 <= score.comm_raw_score() <= 1.0
    assert 0.0 <= score.email_voltage_score() <= 1.0
    assert 0.0 <= score.email_reply_score() <= 1.0
    assert 0.0 <= score.bdf30() <= 1.0
    assert 0.0 <= score.customer_facing_artifact_score() <= 1.0
    assert 0.0 <= score.rpe() <= 1.0
    d = score.to_dict()
    assert set(d) == {"phase_scores", "formulas", "banned_phrases", "reactance_risk"}
    assert d["phase_scores"]["wound_precision"] == 0.85


def test_legacy_gate_engine_report_shape() -> None:
    report = GateEngine.check_gates(example_sarah_chen(), "A quiet, specific message.")
    assert set(report) == {"passed", "blocks", "warnings", "can_ship"}
    assert isinstance(report["blocks"], list)
    assert GateEngine.scan_banned_phrases("Just checking in on this.") == ["just checking in"]
    assert GateEngine.scan_banned_phrases("A clean sentence.") == []


def test_doctrine_weights_and_artifact_scan() -> None:
    for name, weights in FORMULA_WEIGHTS.items():
        assert abs(sum(weights) - 1.0) < 1e-6, name

    clean = validate_doctrine({"memo.md": "A clean artifact with no banned phrases."})
    assert clean.passed is True

    dirty = validate_doctrine({"memo.md": "just checking in\nanyone there?"})
    assert dirty.passed is False
    assert dirty.violations[0].code == "BANNED_PHRASE_IN_ARTIFACT"

    teaching = validate_doctrine({"guide.md": 'do not write just checking in - banned phrase'})
    assert teaching.passed is True

    assert "violations" in validate_doctrine().to_dict()
