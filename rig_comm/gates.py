"""
RIG Communication Protocol - Gate Enforcement Engine.

Every gate is driven by a rule set (see :mod:`rig_comm.rules`): the banned
phrases, the reactance and manipulation markers, the numeric thresholds, and
the per-gate severity (block / warn / off). Blocking failures stop shipment.
Warnings require attention but do not block. Returns structured results.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from math import log2
from collections import Counter

from .rules import (
    DEFAULT_BANNED_PHRASES,
    DEFAULT_REACTANCE_MARKERS,
    RuleSet,
    default_rules,
)
from .scoring import CommunicationScore


# ============================================================================
# Data structures
# ============================================================================

# Legacy module-level aliases. The live lists come from the rule set.
BANNED_PHRASES: List[str] = list(DEFAULT_BANNED_PHRASES)
REACTANCE_MARKERS: List[str] = list(DEFAULT_REACTANCE_MARKERS)


@dataclass
class GateResult:
    """Single gate check result."""
    name: str
    category: str
    passed: bool
    severity: str        # "block" | "warn" | "info"
    message: str
    evidence: List[str] = field(default_factory=list)
    value: Optional[float] = None
    threshold: Optional[float] = None


@dataclass
class GateReport:
    """Full gate enforcement report."""
    passed: bool
    blocks: List[GateResult] = field(default_factory=list)
    warnings: List[GateResult] = field(default_factory=list)
    infos: List[GateResult] = field(default_factory=list)
    all_results: List[GateResult] = field(default_factory=list)
    can_ship: bool = False
    summary: Dict[str, bool] = field(default_factory=dict)


# ============================================================================
# Utility functions
# ============================================================================

def _shannon_entropy(words: List[str]) -> float:
    """Compute Shannon entropy H = -sum(p * log2(p)) for word distribution."""
    if not words:
        return 0.0
    total = len(words)
    counts = Counter(words)
    entropy = 0.0
    for count in counts.values():
        p = count / total
        if p > 0:
            entropy -= p * log2(p)
    return entropy


def compute_entropy_ratio(text: str, baseline_text: str) -> float:
    """H(artifact) / H(median_baseline). Gate: >= entropy_ratio_min."""
    text_words = text.lower().split()
    baseline_words = baseline_text.lower().split()
    h_artifact = _shannon_entropy(text_words)
    h_baseline = _shannon_entropy(baseline_words)
    if h_baseline == 0:
        return float('inf')
    return h_artifact / h_baseline


def compute_reactance_risk(text: str, markers: Optional[List[str]] = None) -> float:
    """ReactanceRisk = sum(ThreatMarkers) / TotalSentences.

    Gate: <= reactance_max (Li & Shi 2025 meta-analysis threshold is 0.20).
    """
    marker_list = markers if markers is not None else REACTANCE_MARKERS
    text_lower = text.lower()
    sentences = [s.strip() for s in text.replace('!', '.').replace('?', '.').split('.') if s.strip()]
    if not sentences:
        return 0.0
    marker_count = sum(1 for marker in marker_list if marker.lower() in text_lower)
    return marker_count / len(sentences)


def _make_result(name: str, category: str, passed: bool, severity: str,
                 message: str, value: Optional[float] = None,
                 threshold: Optional[float] = None,
                 evidence: Optional[List[str]] = None) -> GateResult:
    return GateResult(
        name=name, category=category, passed=passed, severity=severity,
        message=message, value=value, threshold=threshold,
        evidence=evidence or [],
    )


# ============================================================================
# GateEngine
# ============================================================================

class GateEngine:
    """Enforces the universal hard gates for RIG communications.

    Every threshold, phrase list and severity comes from the rule set passed
    to :meth:`check_gates`; with no rule set the shipped doctrine applies.
    """

    BANNED_PHRASES: List[str] = BANNED_PHRASES

    @staticmethod
    def scan_banned_phrases(text: str, rules: Optional[RuleSet] = None) -> List[str]:
        """Scan text for banned phrases (case-insensitive) per the rule set."""
        rules = rules or default_rules()
        text_lower = text.lower()
        return [p for p in rules.banned_phrases if p.lower() in text_lower]

    @staticmethod
    def check_gates(score: CommunicationScore, text: str,
                    baseline_text: str = "professional email regarding business services",
                    extra_context: Optional[Dict] = None,
                    rules: Optional[RuleSet] = None) -> GateReport:
        """Run all gates under the given rule set. Returns a GateReport."""
        rules = rules or default_rules()
        t = {k: rules.threshold(k) for k in rules.thresholds}
        results: List[GateResult] = []

        def add(name: str, category: str, passed: bool, message: str,
                value: Optional[float] = None, threshold: Optional[float] = None,
                evidence: Optional[List[str]] = None) -> None:
            severity = rules.severity(name)
            if severity == "off":
                return
            results.append(_make_result(name, category, passed, severity, message,
                                        value=value, threshold=threshold, evidence=evidence))

        # === Sequence Integrity ===
        passed = score.wound_precision > 0.01
        add("WOUND_MISSING", "sequence", passed,
            "Wound phase present" if passed else "No wound identified",
            score.wound_precision, 0.01)

        passed = score.mirror_accuracy > t["mirror_min"]
        add("MIRROR_MISSING", "sequence", passed,
            "Mirror phase present" if passed else "No mirror - recipient will not feel understood",
            score.mirror_accuracy, t["mirror_min"])

        # === Autonomy ===
        passed = score.autonomy_preservation >= t["autonomy_min"]
        auto_min = t["autonomy_min"]
        add("AUTONOMY", "sequence", passed,
            f"AutonomyPreservation {score.autonomy_preservation:.2f} >= {auto_min:.2f}" if passed
            else f"AutonomyPreservation {score.autonomy_preservation:.2f} < {auto_min:.2f} - chasing detected",
            score.autonomy_preservation, auto_min)

        # === Banned Phrases ===
        banned = GateEngine.scan_banned_phrases(text, rules)
        passed_bp = len(banned) == 0
        add("BANNED_PHRASES", "sequence", passed_bp,
            "No banned phrases found" if passed_bp
            else f"Banned phrases found: {', '.join(banned)}",
            evidence=banned)

        # === Quality Thresholds ===
        passed = score.wound_precision >= t["wound_min"]
        add("WOUND_GENERIC", "quality", passed,
            f"WoundPrecision {score.wound_precision:.2f} {'>=' if passed else '<'} {t['wound_min']:.2f}",
            score.wound_precision, t["wound_min"])

        passed = score.specificity_density >= t["specificity_min"]
        spec_min = t["specificity_min"]
        add("TOO_VAGUE", "quality", passed,
            f"SpecificityDensity {score.specificity_density:.2f} {'>=' if passed else '<'} {spec_min:.2f} - "
            f"{'PASS' if passed else 'Add numbers, names, evidence'}",
            score.specificity_density, spec_min)

        from .formulas import comm_raw_score
        crs = comm_raw_score(score)
        passed_crs = crs >= t["comm_raw_min"]
        add("BELOW_DOCTRINE", "quality", passed_crs,
            f"CommRawScore {crs:.4f} {'>=' if passed_crs else '<'} {t['comm_raw_min']:.2f}",
            crs, t["comm_raw_min"])

        # === Customer-Facing Gates ===
        from .formulas import customer_facing_artifact_score
        cfas = customer_facing_artifact_score(score) * 100  # Scale to 0-100
        passed_cfas = cfas >= t["cfas_min"]
        add("CFAS_FAIL", "customer_facing", passed_cfas,
            f"CFAS {cfas:.1f} {'>=' if passed_cfas else '<'} {t['cfas_min']:.0f}",
            cfas, t["cfas_min"])

        passed_agf = score.anti_generic_force >= t["anti_generic_min"]
        agf_min = t["anti_generic_min"]
        add("INTERCHANGEABLE", "customer_facing", passed_agf,
            f"AntiGenericForce {score.anti_generic_force:.2f} {'>=' if passed_agf else '<'} {agf_min:.2f} - "
            f"{'PASS' if passed_agf else 'Positioning interchangeable'}",
            score.anti_generic_force, agf_min)

        passed_id = score.identity_force >= t["identity_min"]
        id_min = t["identity_min"]
        add("NOT_RIG", "customer_facing", passed_id,
            f"IdentityForce {score.identity_force:.2f} {'>=' if passed_id else '<'} {id_min:.2f} - "
            f"{'PASS' if passed_id else 'Does not feel like RIG'}",
            score.identity_force, id_min)

        passed_rig = score.rig_signature >= t["rig_signature_min"]
        add("GENERIC_SIGNATURE", "customer_facing", passed_rig,
            f"RIGSignature {score.rig_signature:.2f} {'>=' if passed_rig else '<'} {t['rig_signature_min']:.2f}",
            score.rig_signature, t["rig_signature_min"])

        # === Deviation Gates ===
        from .formulas import bdf30
        bdf = bdf30(score)
        # Raw BDF30 formula outputs 0.0-1.0. Full MAD-Z computation
        # (target > 8.0 sigma) requires a median baseline corpus.
        passed_bdf = bdf >= t["bdf30_min"]
        bdf_min = t["bdf30_min"]
        add("BDF30_FAIL", "deviation", passed_bdf,
            f"BDF30 {bdf:.2f} {'>=' if passed_bdf else '<'} {bdf_min:.2f} - "
            f"{'PASS' if passed_bdf else 'Not deviant enough'}",
            bdf, bdf_min)

        if extra_context and 'swarm' in extra_context:
            swarm = extra_context['swarm']
            pred_success = getattr(swarm, 'predicted_success', lambda: 0)()
            passed_ps = pred_success >= t["predicted_success_min"]
            add("PREDICTED_FAIL", "deviation", passed_ps,
                f"PredictedSuccess {pred_success:.2f} {'>=' if passed_ps else '<'} {t['predicted_success_min']:.2f}",
                pred_success, t["predicted_success_min"])

        # === LinkedIn-Specific Gates ===
        if extra_context and extra_context.get('is_linkedin'):
            swarm_consensus = extra_context.get('swarm_consensus', 0)
            passed_sc = swarm_consensus >= t["swarm_consensus_min"]
            add("SWARM_DISAGREE", "linkedin", passed_sc,
                f"SwarmConsensus {swarm_consensus:.2f} {'>=' if passed_sc else '<'} {t['swarm_consensus_min']:.2f}",
                swarm_consensus, t["swarm_consensus_min"])

            hook_rupture = extra_context.get('hook_rupture', 0)
            passed_hr = hook_rupture >= t["hook_rupture_min"]
            hr_min = t["hook_rupture_min"]
            add("HOOK_WEAK", "linkedin", passed_hr,
                f"HookRupture {hook_rupture:.2f} {'>=' if passed_hr else '<'} {hr_min:.2f} - "
                f"hook will not stop the scroll",
                hook_rupture, hr_min)

        # === Ethical Gates ===
        passed_er = score.ethical_restraint >= t["ethical_min"]
        eth_min = t["ethical_min"]
        add("MANIPULATION", "ethical", passed_er,
            f"EthicalRestraint {score.ethical_restraint:.2f} {'>=' if passed_er else '<'} {eth_min:.2f} - "
            f"{'PASS' if passed_er else 'Manipulation risk detected'}",
            score.ethical_restraint, eth_min)

        # Over-explanation (warn by default)
        text_word_count = len(text.split())
        wc_warn = t["word_count_warn"]
        is_over_explaining = text_word_count > wc_warn
        wc_note = f"> {int(wc_warn)} - over-explaining, cut 40%" if is_over_explaining else "OK"
        add("OVER_EXPLAINING", "ethical", not is_over_explaining,
            f"Word count: {text_word_count} ({wc_note})",
            float(text_word_count), wc_warn)

        text_lower = text.lower()
        manipulation_hits = [m for m in rules.manipulation_markers if m.lower() in text_lower]
        passed_manip = len(manipulation_hits) == 0
        add("MANIPULATION_LANGUAGE", "ethical", passed_manip,
            "No manipulation language detected" if passed_manip
            else f"Manipulation language detected: {', '.join(manipulation_hits)}",
            evidence=manipulation_hits)

        # === Entropy Gate ===
        entropy_ratio = compute_entropy_ratio(text, baseline_text)
        passed_entropy = entropy_ratio >= t["entropy_ratio_min"]
        ent_min = t["entropy_ratio_min"]
        add("ENTROPY", "entropy", passed_entropy,
            f"Entropy ratio {entropy_ratio:.3f} {'>=' if passed_entropy else '<'} {ent_min} - "
            f"{'PASS' if passed_entropy else 'Not enough deviation from median'}",
            entropy_ratio, ent_min)

        # === Reactance Gate ===
        reactance = compute_reactance_risk(text, list(rules.reactance_markers))
        react_max = t["reactance_max"]
        passed_react = reactance <= react_max
        add("REACTANCE", "reactance", passed_react,
            f"ReactanceRisk {reactance:.2f} {'<=' if passed_react else '>'} {react_max:.2f} - "
            f"{'PASS' if passed_react else 'Autonomy threat exceeded'}",
            reactance, react_max)

        # === Build report ===
        blocks = [r for r in results if r.severity == "block" and not r.passed]
        warns = [r for r in results if r.severity == "warn" and not r.passed]
        infos = [r for r in results if r.severity == "info"]
        categories = {}
        for r in results:
            cat = r.category
            if cat not in categories:
                categories[cat] = True
            if not r.passed and r.severity == "block":
                categories[cat] = False

        return GateReport(
            passed=len(blocks) == 0,
            blocks=blocks,
            warnings=warns,
            infos=infos,
            all_results=results,
            can_ship=len(blocks) == 0,
            summary=categories,
        )
