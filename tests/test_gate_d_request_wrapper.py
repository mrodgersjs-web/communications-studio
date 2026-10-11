import json
import stat
from pathlib import Path

from rig_comm.integrations.rig_loop_gate_d import (
    build_gate_d_request_command,
    request_gate_d,
)


def _fake_executable(tmp_path: Path, body: str) -> Path:
    exe = tmp_path / "rig-loop-fake.py"
    exe.write_text("#!/usr/bin/env python3\n" + body)
    exe.chmod(exe.stat().st_mode | stat.S_IXUSR)
    return exe


def test_command_uses_supported_action_text_without_target_or_reason_flags(tmp_path):
    cmd = build_gate_d_request_command(
        "send",
        "linkedin:person with spaces",
        "needs approval --target is data, not a flag",
        rig_loop=tmp_path / "rig-loop",
    )

    assert cmd[:4] == [str(tmp_path / "rig-loop"), "gate-d", "request", "--action"]
    assert "--target" not in cmd
    assert "--reason" not in cmd

    marker, raw = cmd[4].split(" ", 1)
    assert marker == "communications-studio"
    # The action text preserves field boundaries as JSON, including flag-like text.
    payload = json.loads(raw.removeprefix("request_effect "))
    assert payload == {
        "action": "send",
        "target": "linkedin:person with spaces",
        "reason": "needs approval --target is data, not a flag",
    }


def test_request_gate_d_reports_missing_executable(tmp_path):
    result = request_gate_d(
        "send",
        "target",
        "reason",
        rig_loop=tmp_path / "missing-rig-loop",
        cwd=tmp_path,
    )

    assert result == {"error": "platform rig-loop unavailable"}


def test_request_gate_d_runs_fake_executable_with_argument_boundaries(tmp_path):
    exe = _fake_executable(
        tmp_path,
        """
import json, sys
print(json.dumps(sys.argv[1:]))
""",
    )

    result = request_gate_d(
        "send outward",
        "target with spaces",
        "reason with --reason and unicode π",
        rig_loop=exe,
        cwd=tmp_path,
    )

    assert result["exit"] == 0
    argv = json.loads(result["stdout"])
    assert argv[:3] == ["gate-d", "request", "--action"]
    assert len(argv) == 4
    assert json.loads(argv[3].removeprefix("communications-studio request_effect ")) == {
        "action": "send outward",
        "target": "target with spaces",
        "reason": "reason with --reason and unicode π",
    }


def test_request_gate_d_returns_nonzero_status_and_stderr(tmp_path):
    exe = _fake_executable(
        tmp_path,
        """
import sys
print('bad args', file=sys.stderr)
sys.exit(7)
""",
    )

    result = request_gate_d("a", "t", "r", rig_loop=exe, cwd=tmp_path)

    assert result["exit"] == 7
    assert "bad args" in result["stderr"]


def test_request_gate_d_reports_timeout_without_retrying_or_mutating(tmp_path):
    exe = _fake_executable(
        tmp_path,
        """
import time
time.sleep(2)
""",
    )

    result = request_gate_d("a", "t", "r", rig_loop=exe, cwd=tmp_path, timeout=0.1)

    assert result["error"] == "platform rig-loop timed out"
    assert result["timeout_seconds"] == 0.1
