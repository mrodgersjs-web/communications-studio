"""Consistency tests: the docs must match the code and the real CLI output.

The README promises that quoted output is real and that its checks can be run.
These tests hold it to that: quoted output is compared against a live run, the
rule reference table is compared against the shipped defaults, and the
changelog version is compared against the package metadata.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

from rig_comm.rules import DEFAULT_THRESHOLDS, GATE_SEVERITIES, THRESHOLD_RANGES

REPO = Path(__file__).resolve().parent.parent


def test_readme_quoted_example_output_matches_real_run() -> None:
    readme = (REPO / "README.md").read_text(encoding="utf-8")
    run = subprocess.run(
        [sys.executable, str(REPO / "examples" / "run_example.py")],
        capture_output=True, text=True, check=True,
    )
    out = run.stdout
    # Every score and decision quoted in the README must appear in the real run.
    assert '"channel_score": 0.773' in readme and '"channel_score": 0.773' in out
    assert '"decision": "EMIT"' in readme and '"decision": "EMIT"' in out
    assert '"decision": "BLOCK"' in readme and '"decision": "BLOCK"' in out
    assert "BANNED_PHRASES: Banned phrases found" in readme
    assert "BANNED_PHRASES: Banned phrases found" in out


def test_readme_quickstart_paths_exist() -> None:
    readme = (REPO / "README.md").read_text(encoding="utf-8")
    assert (REPO / "examples" / "run_example.py").is_file()
    assert (REPO / "examples" / "good_message.txt").is_file()
    assert "python3 examples/run_example.py" in readme


def test_rules_doc_matches_shipped_defaults() -> None:
    doc = (REPO / "docs" / "rules.md").read_text(encoding="utf-8")
    for name, default in DEFAULT_THRESHOLDS.items():
        assert f"`{name}`" in doc, name
        # Each documented default row shows the shipped default value.
        row = re.search(rf"\|\s*`{re.escape(name)}`\s*\|\s*([0-9.]+)", doc)
        assert row, name
        assert abs(float(row.group(1)) - default) < 1e-9, name
    for gate in GATE_SEVERITIES:
        assert gate in doc, gate
    for key in THRESHOLD_RANGES:
        assert key in DEFAULT_THRESHOLDS


def test_changelog_version_matches_package() -> None:
    changelog = (REPO / "CHANGELOG.md").read_text(encoding="utf-8")
    pyproject = (REPO / "pyproject.toml").read_text(encoding="utf-8")
    pkg_version = re.search(r'^version = "([^"]+)"', pyproject, re.M).group(1)
    assert f"## [{pkg_version}]" in changelog


def test_readme_has_no_banned_words() -> None:
    readme = (REPO / "README.md").read_text(encoding="utf-8").lower()
    for word in ("unlock", "empower", "synergy", "leverage", "disrupt",
                 "hustle", "utilize", "iterate", "optimize"):
        assert word not in readme, word
    assert "—" not in readme
