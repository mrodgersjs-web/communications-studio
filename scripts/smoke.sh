#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
python3 -m pip install -e ".[test]" -q
pytest -q
python3 -c 'from rig_comm.cli import main; print("cli_import_ok")'
echo "communications-studio smoke PASS"
