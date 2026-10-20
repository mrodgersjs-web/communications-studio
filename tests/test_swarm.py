"""Tests for the prediction swarm (rig_comm.swarm)."""
from __future__ import annotations

from rig_comm.swarm import PERSONAS, PersonaPrediction, PredictionSwarm, example_swarm


def _pred(persona: str = "P", read: bool = True, trust: float = 0.2, reply: float = 0.3,
          share: float = 0.1, comment: float = 0.1, forward: float = 0.1,
          meeting: float = 0.2) -> PersonaPrediction:
    return PersonaPrediction(
        persona=persona, read_past_line_2=read, trust_delta=trust,
        reply_probability=reply, share_probability=share,
        comment_probability=comment, forward_probability=forward,
        meeting_probability=meeting,
    )


def test_example_swarm_has_all_personas() -> None:
    swarm = example_swarm()
    assert len(swarm.predictions) == len(PERSONAS)
    assert {p.persona for p in swarm.predictions} == set(PERSONAS)


def test_example_swarm_scores_are_in_range() -> None:
    swarm = example_swarm()
    assert 0.0 <= swarm.predicted_success() <= 1.0
    assert 0.0 <= swarm.swarm_consensus() <= 1.0
    # One persona (Competitor Analyst) predicts trust decay.
    assert swarm.has_trust_decay() is True


def test_empty_swarm_is_neutral() -> None:
    swarm = PredictionSwarm()
    assert swarm.predicted_success() == 0.0
    assert swarm.swarm_consensus() == 0.0
    assert swarm.has_trust_decay() is False


def test_predicted_success_weights_read_and_trust() -> None:
    swarm = PredictionSwarm()
    swarm.add_prediction(_pred(read=False, trust=0.0, reply=0.0, share=0.0,
                               comment=0.0, forward=0.0, meeting=0.0))
    assert swarm.predicted_success() == 0.0

    swarm2 = PredictionSwarm()
    swarm2.add_prediction(_pred(read=True, trust=0.0, reply=0.0, share=0.0,
                                comment=0.0, forward=0.0, meeting=0.0))
    assert abs(swarm2.predicted_success() - 0.10) < 1e-9


def test_swarm_consensus_unity_when_deltas_agree() -> None:
    swarm = PredictionSwarm()
    for i in range(4):
        swarm.add_prediction(_pred(persona=f"P{i}", trust=0.3))
    assert swarm.swarm_consensus() == 1.0

    swarm.add_prediction(_pred(persona="outlier", trust=-0.9))
    assert swarm.swarm_consensus() < 1.0


def test_brier_score_records_history() -> None:
    swarm = PredictionSwarm()
    perfect = swarm.brier_score({"a": 0.5}, {"a": 0.5})
    assert perfect == 0.0
    assert swarm.brier_score({"a": 1.0}, {"a": 0.0}) == 1.0
    # No common keys returns 1.0 and is not recorded.
    assert swarm.brier_score({}, {"a": 1.0}) == 1.0
    assert len(swarm.brier_history) == 2
