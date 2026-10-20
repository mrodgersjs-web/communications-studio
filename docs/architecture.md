# Architecture

## One-liner

A message goes in, a score and a block/emit decision come out, and every rule
behind that decision lives in one validated file.

## Flow

```text
message -> phase cues -> CommunicationScore -> channel formula
        -> gate engine (rule set) -> EMIT or BLOCK (with reasons)
```

1. `rig_comm/core.py` derives phase scores from cue words in the text (wound,
   mirror, autonomy, qualification, open loop) plus specificity density from
   numbers, proper nouns, and evidence words. The result is a
   `CommunicationScore` (dataclass, see `rig_comm/scoring.py`).
2. `rig_comm/formulas.py` turns the score into the channel formulas:
   `comm_raw_score`, `email_voltage_score`, `email_reply_score`, `bdf30`,
   `customer_facing_artifact_score`, plus the IDP sub-scores used by the idea
   tournament.
3. `rig_comm/gates.py` runs every gate against the score and the raw text. Each
   gate reads its threshold, phrase lists, and severity from the rule set.
4. A gate severity of `block` failing means `can_ship = false` (CLI exit 2).
   `warn` prints and ships. `off` skips the gate entirely.

## The rule set

`rig_comm/rules.py` owns the schema: `banned_phrases`, `reactance_markers`,
`manipulation_markers`, `thresholds`, `severities`. Loading is strict YAML or
JSON; every unknown key, wrong type, and out-of-range value is reported in one
`RuleValidationError`. Defaults are the shipped doctrine, so the engine works
with no rule file at all. See [rules.md](rules.md).

## Module map

| Module | Role |
| --- | --- |
| `rig_comm/rules.py` | Rule set schema, defaults, YAML/JSON loading, validation |
| `rig_comm/gates.py` | Gate engine (entropy, reactance, banned phrases, quality gates) |
| `rig_comm/core.py` | `evaluate()`: text + channel + rules to a `Report` |
| `rig_comm/formulas.py` | Channel formulas and IDP sub-scores |
| `rig_comm/scoring.py` | `CommunicationScore` container (V10 methods kept for compatibility) |
| `rig_comm/tournament.py` | Six-round idea tournament over signal cards |
| `rig_comm/swarm.py` | Eight-persona prediction swarm with Brier scoring |
| `rig_comm/cli.py` | `rig` entry point: evaluate, gate, score, rules-validate, doctrine-check, run-workflow |
| `src/*.py` | Thin compatibility shims that run the real modules |

## Design notes

- Gate evaluation is pure: same text and same rule set always produce the same
  report. The only randomness lives in the tournament's simulated adversary
  checks.
- The rule set is immutable once loaded (`RuleSet` is a frozen dataclass), so a
  report can always name the rules it was judged under.
- Messages over the `word_count_warn` threshold warn but ship: length is a
  quality signal, not a safety one.
- The entropy gate compares word-distribution entropy against a median baseline
  phrase. It exists to catch copy that is statistically indistinguishable from
  filler.
- Legacy layers (`rig_comm/scoring.py` V10 engine, `src/` shims) stay because
  external callers use them. New behavior goes into `rules.py` and `gates.py`.

## Trust boundaries

- Public inputs only in examples and fixtures.
- Secrets never enter the repo or a rule file.
- Rule files are local configuration; loading one never executes code (YAML is
  parsed with `safe_load`).
