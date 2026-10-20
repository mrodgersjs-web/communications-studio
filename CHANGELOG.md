# Changelog

All notable changes to this project are documented here.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [11.1.0] - 2026-10-19

Polish wave (2026-10-19, same day, this commit): `.github/CODEOWNERS`
(`* @mrodgersjs-web`) and `.github/copilot-instructions.md` were added,
`timeout-minutes: 15` was added to every job in `.github/workflows/ci.yml`,
`rig-lattice.yml` and `smoke.yml`, and `tests/test_repo_hygiene.py` was added.
That test asserts from the files on disk that `.github/CODEOWNERS` contains
`* @mrodgersjs-web`, that `.github/copilot-instructions.md` exists within
8000 bytes and names a test command, that the README carries a
`github/actions/workflow/status` badge, the `rodgersintelligence.com` footer,
a test command word and clone examples targeting
`mrodgersjs-web/communications-studio`, and that every workflow job has
`timeout-minutes` and no `continue-on-error`.


### Added
- Configurable rule sets: load banned phrases, reactance markers, manipulation
  markers, gate thresholds, and per-gate severities (block / warn / off) from a
  YAML or JSON file (`rig_comm/rules.py`).
- Strict rule validation that lists every problem: unknown keys, wrong types,
  out-of-range thresholds, unknown gate names.
- CLI: `--rules <file>` on `evaluate`, `gate`, and `score`; new `rig
  rules-validate <file>` command.
- Runnable example (`examples/run_example.py`) with a passing and a blocked
  message, plus an example rule file (`examples/rules.yaml`).
- Test suite for rules loading, validation, gate wiring, and the CLI.
- Community files: code of conduct, issue templates, pull request template,
  Dependabot config.

### Changed
- Gate engine (`rig_comm/gates.py`) now takes its thresholds and phrase lists
  from the rule set instead of hardcoded constants.
- Packaging: version 11.1.0, requires Python >= 3.10, typed package marker
  (`py.typed`), ruff configuration, project URLs, coverage-based CI matrix
  (Python 3.10 to 3.13).
- README rewritten with a real example message, its real score, and the real
  block/emit output.

### Removed
- Print-only gate demo harness (its checks now live in the test suite and the
  shipped example).

## [11.0.0] - 2026-09-20

### Added
- Scoring formulas, gate engine, doctrine checks, CLI, and AgentForge workflows.
