"""Safe Gate-D request wrapper for the platform rig-loop CLI.

The current rig-loop contract accepts one documented request payload:
``rig-loop gate-d request --action <text>`` (plus run-selection flags such as
``--run``/``--cwd``). It does not accept separate ``--target`` or ``--reason``
flags. This module preserves the MCP tool's action/target/reason fields inside
that supported action text and never executes the requested outward effect.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

DEFAULT_RIG_LOOP = Path.home() / "Developer/rig-capabilities/bin/rig-loop"
DEFAULT_TIMEOUT_SECONDS = 10


def gate_d_action_text(action: str, target: str, reason: str) -> str:
    """Return the exact string stored as rig-loop's Gate-D requested action."""
    payload = {"action": action, "target": target, "reason": reason}
    return "communications-studio request_effect " + json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def build_gate_d_request_command(
    action: str,
    target: str,
    reason: str,
    *,
    rig_loop: Path | str = DEFAULT_RIG_LOOP,
) -> list[str]:
    """Build the documented rig-loop Gate-D request command.

    ``action``, ``target`` and ``reason`` are data inside the supported
    ``--action`` value. They are not emitted as unsupported CLI flags.
    """
    return [
        str(rig_loop),
        "gate-d",
        "request",
        "--action",
        gate_d_action_text(action, target, reason),
    ]


def request_gate_d(
    action: str,
    target: str,
    reason: str,
    *,
    rig_loop: Path | str = DEFAULT_RIG_LOOP,
    cwd: Path | str,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    """Queue a Gate-D approval request through rig-loop; never perform an effect."""
    rig_loop_path = Path(rig_loop)
    if not rig_loop_path.exists():
        return {"error": "platform rig-loop unavailable"}

    cmd = build_gate_d_request_command(action, target, reason, rig_loop=rig_loop_path)
    try:
        run = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=cwd,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        return {
            "error": "platform rig-loop timed out",
            "timeout_seconds": timeout,
            "stdout": (exc.stdout or "")[-800:],
            "stderr": (exc.stderr or "")[-400:],
        }

    return {
        "exit": run.returncode,
        "stdout": run.stdout[-800:],
        "stderr": run.stderr[-400:],
    }
