#!/usr/bin/env python3
"""Run the gate engine over the two example messages.

Usage: python3 examples/run_example.py

Prints each message's channel score and the block/emit decision. This is the
exact output quoted in the README.
"""
from __future__ import annotations

import json
from pathlib import Path

from rig_comm import evaluate

HERE = Path(__file__).resolve().parent


def main() -> int:
    for name in ("good_message.txt", "blocked_message.txt"):
        text = (HERE / name).read_text(encoding="utf-8")
        report = evaluate(text, channel="email")
        decision = "EMIT" if report.can_ship else "BLOCK"
        print(f"=== {name} ===")
        print(json.dumps({
            "channel_formula": report.channel_formula,
            "channel_score": round(report.channel_score, 4),
            "comm_raw_score": round(report.comm_raw_score, 4),
            "decision": decision,
            "blocks": report.blocks,
            "warnings": report.warnings,
        }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
