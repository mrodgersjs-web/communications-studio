"""Configurable rule set for the communication gate engine.

A rule set is a YAML or JSON document that controls what the gate engine
blocks, warns about, or ignores:

- ``banned_phrases``: phrases that always block a message.
- ``reactance_markers``: imperative language that raises reactance risk.
- ``manipulation_markers``: overclaim language that lowers ethical restraint.
- ``thresholds``: numeric gate thresholds keyed by gate name.
- ``severities``: per-gate severity, one of ``block``, ``warn``, ``off``.

Loading is strict: unknown keys, wrong types, and out-of-range values raise
:class:`RuleValidationError` with every problem listed, so a bad rule file
fails fast instead of silently weakening a gate.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Tuple

# ---------------------------------------------------------------------------
# Defaults (the shipped doctrine)
# ---------------------------------------------------------------------------

DEFAULT_BANNED_PHRASES: Tuple[str, ...] = (
    "just checking in",
    "following up",
    "touching base",
    "would love to chat",
    "let me know your thoughts",
    "happy to help",
    "hope this finds you well",
    "i wanted to reach out",
    "quick question",
    "looking forward to hearing from you",
)

DEFAULT_REACTANCE_MARKERS: Tuple[str, ...] = (
    "you must",
    "you need to",
    "you have to",
    "don't miss",
    "act now",
    "urgent",
    "limited time",
    "before it's too late",
    "you should",
    "you'd be crazy not to",
    "you're making a mistake",
    "I need you to",
    "I require",
    "demand",
    "insist",
    "asap",
    "immediately",
    "right now",
    "today only",
    "last chance",
    "don't wait",
    "hurry",
)

DEFAULT_MANIPULATION_MARKERS: Tuple[str, ...] = (
    "guaranteed",
    "100%",
    "zero risk",
    "foolproof",
)

# Threshold keys and their valid numeric ranges.
THRESHOLD_RANGES: Dict[str, Tuple[float, float]] = {
    "wound_min": (0.0, 1.0),
    "mirror_min": (0.0, 1.0),
    "autonomy_min": (0.0, 1.0),
    "specificity_min": (0.0, 1.0),
    "comm_raw_min": (0.0, 1.0),
    "cfas_min": (0.0, 100.0),
    "anti_generic_min": (0.0, 1.0),
    "identity_min": (0.0, 1.0),
    "rig_signature_min": (0.0, 1.0),
    "bdf30_min": (0.0, 1.0),
    "predicted_success_min": (0.0, 1.0),
    "swarm_consensus_min": (0.0, 1.0),
    "hook_rupture_min": (0.0, 1.0),
    "ethical_min": (0.0, 1.0),
    "entropy_ratio_min": (0.0, 10.0),
    "reactance_max": (0.0, 1.0),
    "word_count_warn": (1.0, 100000.0),
}

DEFAULT_THRESHOLDS: Dict[str, float] = {
    "wound_min": 0.60,
    "mirror_min": 0.01,
    "autonomy_min": 0.70,
    "specificity_min": 0.50,
    "comm_raw_min": 0.65,
    "cfas_min": 82.0,
    "anti_generic_min": 0.80,
    "identity_min": 0.75,
    "rig_signature_min": 0.75,
    "bdf30_min": 0.85,
    "predicted_success_min": 0.82,
    "swarm_consensus_min": 0.65,
    "hook_rupture_min": 0.70,
    "ethical_min": 0.70,
    "entropy_ratio_min": 1.2,
    "reactance_max": 0.20,
    "word_count_warn": 200.0,
}

# Gate name -> default severity. "off" skips the gate entirely.
GATE_SEVERITIES: Dict[str, str] = {
    "WOUND_MISSING": "block",
    "MIRROR_MISSING": "block",
    "AUTONOMY": "block",
    "BANNED_PHRASES": "block",
    "WOUND_GENERIC": "block",
    "TOO_VAGUE": "block",
    "BELOW_DOCTRINE": "block",
    "CFAS_FAIL": "block",
    "INTERCHANGEABLE": "block",
    "NOT_RIG": "block",
    "GENERIC_SIGNATURE": "block",
    "BDF30_FAIL": "block",
    "PREDICTED_FAIL": "block",
    "SWARM_DISAGREE": "block",
    "HOOK_WEAK": "block",
    "MANIPULATION": "block",
    "OVER_EXPLAINING": "warn",
    "MANIPULATION_LANGUAGE": "block",
    "ENTROPY": "block",
    "REACTANCE": "block",
}

VALID_SEVERITIES = ("block", "warn", "off")

TOP_LEVEL_KEYS = ("banned_phrases", "reactance_markers", "manipulation_markers", "thresholds", "severities")


class RuleValidationError(ValueError):
    """Raised when a rule set document is invalid. Lists every problem."""

    def __init__(self, problems: List[str]):
        self.problems = problems
        super().__init__("invalid rule set: " + "; ".join(problems))


@dataclass(frozen=True)
class RuleSet:
    """An immutable, validated rule set."""

    banned_phrases: Tuple[str, ...] = DEFAULT_BANNED_PHRASES
    reactance_markers: Tuple[str, ...] = DEFAULT_REACTANCE_MARKERS
    manipulation_markers: Tuple[str, ...] = DEFAULT_MANIPULATION_MARKERS
    thresholds: Mapping[str, float] = field(default_factory=lambda: dict(DEFAULT_THRESHOLDS))
    severities: Mapping[str, str] = field(default_factory=lambda: dict(GATE_SEVERITIES))

    def threshold(self, name: str) -> float:
        return float(self.thresholds[name])

    def severity(self, gate_name: str) -> str:
        return self.severities.get(gate_name, "block")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "banned_phrases": list(self.banned_phrases),
            "reactance_markers": list(self.reactance_markers),
            "manipulation_markers": list(self.manipulation_markers),
            "thresholds": dict(self.thresholds),
            "severities": dict(self.severities),
        }


def default_rules() -> RuleSet:
    """The shipped rule set: every threshold and gate at doctrine defaults."""
    return RuleSet()


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def _validate_phrase_list(name: str, value: Any, problems: List[str]) -> Optional[Tuple[str, ...]]:
    if not isinstance(value, list):
        problems.append(f"{name} must be a list of strings, got {type(value).__name__}")
        return None
    out: List[str] = []
    seen = set()
    for i, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            problems.append(f"{name}[{i}] must be a non-empty string")
            continue
        key = item.strip().lower()
        if key in seen:
            problems.append(f"{name}[{i}] duplicates '{item.strip()}'")
            continue
        seen.add(key)
        out.append(item.strip())
    return tuple(out)


def _validate_thresholds(value: Any, problems: List[str]) -> Optional[Dict[str, float]]:
    if not isinstance(value, Mapping):
        problems.append(f"thresholds must be a mapping, got {type(value).__name__}")
        return None
    out = dict(DEFAULT_THRESHOLDS)
    for key, raw in value.items():
        if key not in THRESHOLD_RANGES:
            problems.append(f"thresholds.{key} is not a known threshold")
            continue
        if isinstance(raw, bool) or not isinstance(raw, (int, float)):
            problems.append(f"thresholds.{key} must be a number, got {type(raw).__name__}")
            continue
        lo, hi = THRESHOLD_RANGES[key]
        if not (lo <= float(raw) <= hi):
            problems.append(f"thresholds.{key}={raw} outside valid range [{lo}, {hi}]")
            continue
        out[key] = float(raw)
    return out


def _validate_severities(value: Any, problems: List[str]) -> Optional[Dict[str, str]]:
    if not isinstance(value, Mapping):
        problems.append(f"severities must be a mapping, got {type(value).__name__}")
        return None
    out = dict(GATE_SEVERITIES)
    for key, raw in value.items():
        if key not in GATE_SEVERITIES:
            problems.append(f"severities.{key} is not a known gate name")
            continue
        # YAML reads a bare `off`/`on` as booleans; accept the obvious meaning.
        if raw is False:
            raw = "off"
        elif raw is True:
            raw = "block"
        if raw not in VALID_SEVERITIES:
            problems.append(f"severities.{key}={raw!r} must be one of {list(VALID_SEVERITIES)}")
            continue
        out[key] = raw
    return out


def validate_rules(data: Any) -> RuleSet:
    """Validate a parsed rule document and return a :class:`RuleSet`.

    Raises :class:`RuleValidationError` listing every problem found.
    """
    if not isinstance(data, Mapping):
        raise RuleValidationError([f"rule set must be a mapping, got {type(data).__name__}"])

    problems: List[str] = []
    for key in data:
        if key not in TOP_LEVEL_KEYS:
            problems.append(f"unknown key '{key}'")

    phrases = (
        _validate_phrase_list("banned_phrases", data["banned_phrases"], problems)
        if "banned_phrases" in data else None
    )
    reactance = (
        _validate_phrase_list("reactance_markers", data["reactance_markers"], problems)
        if "reactance_markers" in data else None
    )
    manipulation = (
        _validate_phrase_list("manipulation_markers", data["manipulation_markers"], problems)
        if "manipulation_markers" in data else None
    )
    thresholds = _validate_thresholds(data["thresholds"], problems) if "thresholds" in data else None
    severities = _validate_severities(data["severities"], problems) if "severities" in data else None

    if problems:
        raise RuleValidationError(problems)

    return RuleSet(
        banned_phrases=phrases if phrases is not None else DEFAULT_BANNED_PHRASES,
        reactance_markers=reactance if reactance is not None else DEFAULT_REACTANCE_MARKERS,
        manipulation_markers=manipulation if manipulation is not None else DEFAULT_MANIPULATION_MARKERS,
        thresholds=thresholds if thresholds is not None else dict(DEFAULT_THRESHOLDS),
        severities=severities if severities is not None else dict(GATE_SEVERITIES),
    )


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------

def _load_yaml(text: str, source: str) -> Any:
    try:
        import yaml
    except ImportError as exc:  # pragma: no cover - depends on environment
        raise RuleValidationError(
            [f"{source}: YAML rule files need PyYAML (pip install pyyaml)"]
        ) from exc
    try:
        return yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise RuleValidationError([f"{source}: not valid YAML ({exc})"]) from exc


def load_rules(path: str | Path) -> RuleSet:
    """Load and validate a rule set from a ``.yaml``, ``.yml`` or ``.json`` file."""
    p = Path(path)
    if not p.is_file():
        raise RuleValidationError([f"{p}: file not found"])
    text = p.read_text(encoding="utf-8")
    suffix = p.suffix.lower()
    if suffix == ".json":
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise RuleValidationError([f"{p}: not valid JSON ({exc})"]) from exc
    elif suffix in (".yaml", ".yml"):
        data = _load_yaml(text, str(p))
    else:
        raise RuleValidationError([f"{p}: unsupported extension {suffix!r}, use .yaml, .yml or .json"])
    return validate_rules(data)


def dump_rules(rules: RuleSet) -> str:
    """Serialize a rule set as indented JSON (valid YAML too)."""
    return json.dumps(rules.to_dict(), indent=2, sort_keys=False) + "\n"
