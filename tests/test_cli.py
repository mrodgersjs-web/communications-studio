"""Tests for rig_comm.cli.main: exit codes and JSON output for the evaluate,
gate, score and rules-validate subcommands, plus the shipped example script."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from rig_comm.cli import main

REPO = Path(__file__).resolve().parent.parent
EXAMPLES = REPO / "examples"


def test_cli_evaluate_emits(capsys) -> None:
    text = (EXAMPLES / "good_message.txt").read_text(encoding="utf-8")
    code = main(["evaluate", text, "--channel", "email"])
    out = json.loads(capsys.readouterr().out)
    assert code == 0
    assert out["can_ship"] is True


def test_cli_gate_blocks_with_exit_code_2(capsys, tmp_path) -> None:
    f = tmp_path / "msg.txt"
    f.write_text("Hope this finds you well. Quick question for you.", encoding="utf-8")
    code = main(["gate", str(f), "--channel", "email"])
    out = json.loads(capsys.readouterr().out)
    assert code == 2
    assert out["can_ship"] is False
    assert out["blocks"]


def test_cli_score_prints_formula_values(capsys) -> None:
    f = EXAMPLES / "good_message.txt"
    code = main(["score", str(f), "--channel", "email"])
    out = json.loads(capsys.readouterr().out)
    assert code == 0
    assert out["channel_formula"] == "email_voltage_score"
    assert 0.0 <= out["channel_score"] <= 1.0


def test_cli_custom_rules_flag_blocks(capsys, tmp_path) -> None:
    f = tmp_path / "msg.txt"
    f.write_text("Attaching the deck you asked for.", encoding="utf-8")
    rules = tmp_path / "rules.yaml"
    rules.write_text("banned_phrases:\n  - attaching the deck\n", encoding="utf-8")
    code = main(["gate", str(f), "--rules", str(rules)])
    out = json.loads(capsys.readouterr().out)
    assert code == 2
    assert any("BANNED_PHRASES" in b for b in out["blocks"])


def test_cli_rules_validate_ok(capsys) -> None:
    code = main(["rules-validate", str(EXAMPLES / "rules.yaml")])
    out = json.loads(capsys.readouterr().out)
    assert code == 0
    assert out["valid"] is True
    assert "per my last email" in out["rules"]["banned_phrases"]


def test_cli_rules_validate_bad_file(capsys, tmp_path) -> None:
    bad = tmp_path / "rules.json"
    bad.write_text(json.dumps({"thresholds": {"autonomy_min": 9}}), encoding="utf-8")
    code = main(["rules-validate", str(bad)])
    out = json.loads(capsys.readouterr().out)
    assert code == 1
    assert out["valid"] is False
    assert "outside valid range" in out["error"]


def test_cli_unknown_command() -> None:
    with pytest.raises(SystemExit):
        main([])


def test_shipped_example_runs() -> None:
    import runpy

    with pytest.raises(SystemExit) as excinfo:
        runpy.run_path(str(EXAMPLES / "run_example.py"), run_name="__main__")
    assert excinfo.value.code == 0
