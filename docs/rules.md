# Rule set reference

A rule set is a YAML or JSON file that controls what the gate engine blocks,
warns about, or ignores. Every key is optional; anything you leave out keeps
the doctrine default.

```yaml
banned_phrases:            # phrases that always block (matched case-insensitive)
  - per my last email
reactance_markers:         # imperative language counted by the reactance gate
  - act now
manipulation_markers:      # overclaim language that lowers ethical restraint
  - guaranteed
thresholds:
  autonomy_min: 0.70       # AutonomyPreservation floor
  word_count_warn: 150     # words before the over-explaining warning
severities:
  ENTROPY: off             # block (default) | warn | off
  OVER_EXPLAINING: warn
```

## Validation

Loading is strict. `rig rules-validate rules.yaml` prints every problem it
finds and exits 1 on any of:

- unknown top-level keys, unknown threshold names, unknown gate names
- phrase lists that are not lists of non-empty strings, or that repeat an entry
- thresholds that are not numbers or fall outside their valid range
- severities that are not `block`, `warn`, or `off`

A bare `off` or `on` in YAML parses as a boolean. That is accepted and read as
`off` (false) or `block` (true).

## Thresholds

| Key | Default | Range | Gate |
| --- | --- | --- | --- |
| `wound_min` | 0.60 | 0-1 | WOUND_GENERIC |
| `mirror_min` | 0.01 | 0-1 | MIRROR_MISSING |
| `autonomy_min` | 0.70 | 0-1 | AUTONOMY |
| `specificity_min` | 0.50 | 0-1 | TOO_VAGUE |
| `comm_raw_min` | 0.65 | 0-1 | BELOW_DOCTRINE |
| `cfas_min` | 82 | 0-100 | CFAS_FAIL |
| `anti_generic_min` | 0.80 | 0-1 | INTERCHANGEABLE |
| `identity_min` | 0.75 | 0-1 | NOT_RIG |
| `rig_signature_min` | 0.75 | 0-1 | GENERIC_SIGNATURE |
| `bdf30_min` | 0.85 | 0-1 | BDF30_FAIL |
| `predicted_success_min` | 0.82 | 0-1 | PREDICTED_FAIL |
| `swarm_consensus_min` | 0.65 | 0-1 | SWARM_DISAGREE |
| `hook_rupture_min` | 0.70 | 0-1 | HOOK_WEAK |
| `ethical_min` | 0.70 | 0-1 | MANIPULATION |
| `entropy_ratio_min` | 1.2 | 0-10 | ENTROPY |
| `reactance_max` | 0.20 | 0-1 | REACTANCE |
| `word_count_warn` | 200 | 1-100000 | OVER_EXPLAINING |

## Gate names

`WOUND_MISSING`, `MIRROR_MISSING`, `AUTONOMY`, `BANNED_PHRASES`,
`WOUND_GENERIC`, `TOO_VAGUE`, `BELOW_DOCTRINE`, `CFAS_FAIL`,
`INTERCHANGEABLE`, `NOT_RIG`, `GENERIC_SIGNATURE`, `BDF30_FAIL`,
`PREDICTED_FAIL`, `SWARM_DISAGREE`, `HOOK_WEAK`, `MANIPULATION`,
`OVER_EXPLAINING`, `MANIPULATION_LANGUAGE`, `ENTROPY`, `REACTANCE`.

## Using a rule set

```bash
rig gate draft.txt --rules rules.yaml
rig score draft.txt --rules rules.json
rig rules-validate rules.yaml
```

From Python:

```python
from rig_comm import evaluate, load_rules

rules = load_rules("rules.yaml")
report = evaluate(text, channel="email", rules=rules)
print(report.can_ship, report.blocks)
```

The shipped defaults live in `rig_comm/rules.py` and are exercised by
`examples/rules.yaml`.
