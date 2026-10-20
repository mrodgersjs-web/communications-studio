# communications-studio

Checks AI-drafted messages against your writing rules and blocks the ones that
fail. The scoring core (`rig_comm/`) grades a draft on specific, measurable
signals (wound precision, specificity, reactance risk, banned phrases) and
refuses to ship the ones that fail; the rules live in a YAML or JSON file the
user edits, so the gate matches their standards instead of a hardcoded list.
CLI entry points and the agent tooling sit in `agentforge/` and `src/`.

## Layout

- `rig_comm/` - scoring core and rule loading. `src/`, `agentforge/` - CLI and
  agent-facing surfaces.
- `scores/` - rule sets and score outputs. `templates/` - message templates.
- `tests/` - pytest suite. `examples/` - runnable examples, including
  `examples/run_example.py`. `docs/`, `references/` - design notes and sources.

## Setup and test (exact commands)

```bash
python3 -m pip install -e .
python3 -m pytest -q
python3 -m pytest -q --cov=rig_comm
```

The suite includes tests that flip a gate decision by editing only the rule
file; keep that property when changing rule loading.

## Lint

```bash
ruff check .
```

Must be clean before a PR, together with `pytest -q`.

## Conventions

- Conventional commit subjects (`feat:`, `fix:`, `test:`, `docs:`, `chore:`).
- Every change ships a test that can fail.
- No secrets, tokens or credentials in tracked files. No machine-specific
  paths (`/Users/...`, `~/Developer/...`) in tracked files.
- Numbers in docs and README must come from a command you ran; quote the
  command, not a remembered figure. If a number changes, re-run the command.
