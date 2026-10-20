from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rig_comm.gates import *  # noqa: F401,F403
from rig_comm.gates import GateEngine, compute_reactance_risk  # noqa: F401


if __name__ == "__main__":
    # Backward-compat demo: run the shipped example through the gate engine.
    import json
    from pathlib import Path

    from rig_comm import evaluate

    root = Path(__file__).resolve().parents[1]
    text = (root / "examples" / "good_message.txt").read_text(encoding="utf-8")
    report = evaluate(text, channel="email")
    print(json.dumps({"can_ship": report.can_ship, "blocks": report.blocks}, indent=2))
