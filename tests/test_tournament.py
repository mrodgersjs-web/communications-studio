"""Tests for the idea tournament (rig_comm.tournament)."""
from __future__ import annotations

from rig_comm.tournament import (
    AngleCard,
    AngleGenerator,
    IdeaTournament,
    SignalCard,
    round_1_generate,
    round_2_idp_scoring,
    round_3_adversarial,
    round_4_research_depth,
    round_5_ensemble_draft,
    round_6_learning,
)


def _signals() -> list[SignalCard]:
    return [
        SignalCard("S1: Orthodoxy Hardening", "best practice hardening", "src-a", 0.8, 0.3),
        SignalCard("S2: Wound Frequency", "wound frequency rising", "src-b", 0.7, 0.7),
        SignalCard("S3: Vocabulary Drift", "vocabulary drift detected", "src-c", 0.6, 0.2),
        SignalCard("S4: Villain Emergence", "villain emerging", "src-d", 0.9, 0.5),
        SignalCard("S5: Proof Gaps", "proof gap open", "src-e", 0.75, 0.4),
    ]


def test_signal_card_decay() -> None:
    assert SignalCard("S1", "r", "s", 0.5, 0.7).is_decaying() is True
    assert SignalCard("S1", "r", "s", 0.5, 0.3).is_decaying() is False


def test_generator_is_deterministic_and_multi_layer() -> None:
    a1 = AngleGenerator(seed=7).generate_from_signals(_signals(), count=12)
    a2 = AngleGenerator(seed=7).generate_from_signals(_signals(), count=12)
    assert [a.id for a in a1] == [a.id for a in a2]
    assert len(a1) == 12
    assert len({a.id for a in a1}) == 12
    assert all(len(a.signal_layers) >= 2 for a in a1)
    assert all(a.raw_angle for a in a1)


def test_round_2_kills_single_layer_and_keeps_top_n() -> None:
    angles = round_1_generate(_signals(), 30)
    angles.append(AngleCard(id="SINGLE-1", signal_layers=["S1: Orthodoxy Hardening"],
                            raw_angle="one layer only"))
    report = round_2_idp_scoring(angles, keep_count=10)
    assert report.round_number == 2
    assert report.output_count == len(report.survivors) <= 10
    assert "SINGLE-1" in report.kills
    survivors = [a for a in angles if a.id in report.survivors]
    assert all(not a.killed for a in survivors)
    assert all(a.idp_score >= 0.65 for a in survivors)


def test_rounds_3_to_6_run_and_report() -> None:
    angles = round_1_generate(_signals(), 12)
    r2 = round_2_idp_scoring(angles, keep_count=8)
    kept = [a for a in angles if a.id in r2.survivors] or angles[:3]
    assert r2.round_number == 2

    r3 = round_3_adversarial(kept, keep_count=4)
    assert r3.round_number == 3
    assert r3.output_count == len(r3.survivors) <= 4

    kept3 = [a for a in kept if a.id in r3.survivors] or kept[:2]
    r4 = round_4_research_depth(kept3, keep_count=2)
    assert r4.round_number == 4

    # Later rounds may legitimately kill everything, so the ensemble round is
    # also exercised directly on a non-empty field.
    kept4 = [a for a in kept3 if a.id in r4.survivors] or kept3[:2]
    r5 = round_5_ensemble_draft(kept4)
    assert r5.round_number == 5
    if r5.output_count:
        winner_id = r5.survivors[0]
        winner = next(a for a in kept4 if a.id == winner_id)
    else:
        winner = kept4[0]

    r6 = round_6_learning(winner, brier_accuracy=0.81)
    assert r6.round_number == 6
    assert r6.survivors == [winner.id]
    assert "0.810" in r6.notes


def test_full_tournament_end_to_end(capsys) -> None:
    tournament = IdeaTournament(seed=42)
    report = tournament.run(signals=_signals(), target_angles=24)
    assert report.initial_angle_count == 24
    assert [r.round_number for r in report.rounds] == [1, 2, 3, 4, 5, 6]
    assert report.final_winner is not None
    assert report.final_winner.raw_angle
    assert report.total_killed >= 0
    assert tournament.report is report

    tournament.print_report()
    out = capsys.readouterr().out
    assert "Tournament" in out or "tournament" in out


def test_tournament_without_signals_uses_defaults() -> None:
    report = IdeaTournament(seed=1).run()
    assert report.final_winner is not None
    assert len(report.rounds) == 6
