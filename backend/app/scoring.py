"""
Score a live ContinuityReport against a demo's ground_truth.

This is deterministic Python — it never invents flags. It only checks whether
the *already produced* LLM flags cover planted issues and avoid decoys.
"""
from __future__ import annotations

from app.models.schema import ContinuityReport

PLANTED_TYPES = {
    "contradiction",
    "state_violation",
    "unresolved_thread",
    "unresolved_thread_or_state_violation",
    "timeline_contradiction",
    "legal_clearance",
    "legal_clearance_medium_risk",
    "legal_clearance_high_risk",
}

DECOY_TYPES = {
    "not_a_conflict",
    "not_a_flag",
    "note",
    "legal_clearance_low_risk",
}


def _norm(text: str) -> set[str]:
    return {w for w in "".join(ch.lower() if ch.isalnum() else " " for ch in text).split() if len(w) > 2}


def _overlap(expected_scenes: list[str], actual_scenes: list[str]) -> bool:
    if not expected_scenes:
        return False
    exp, act = set(expected_scenes), set(actual_scenes)
    if exp & act:
        return True
    # scene ids may differ in hyphen/underscore; compare suffixes
    exp_suffix = {s.split("-scene-")[-1] for s in exp}
    act_suffix = {s.split("-scene-")[-1] for s in act}
    return bool(exp_suffix & act_suffix)


def _conflict_matches_gt(gt: dict, report: ContinuityReport) -> bool:
    expected = gt.get("expected_scenes") or []
    gt_words = _norm(gt.get("description", ""))
    for c in report.conflicts:
        scenes_ok = _overlap(expected, c.source_scene_ids) if expected else True
        if not scenes_ok:
            continue
        blob = _norm(f"{c.summary} {c.explanation} {c.entity_name or ''}")
        if not gt_words or len(gt_words & blob) >= 1:
            return True
    if str(gt.get("type", "")).startswith("legal"):
        for f in report.clearance_flags:
            if expected and not _overlap(expected, [f.scene_id]):
                continue
            blob = _norm(f"{f.reference_text} {f.risk_note}")
            if not gt_words or len(gt_words & blob) >= 1:
                return True
    return False


def _decoy_was_flagged(gt: dict, report: ContinuityReport) -> bool:
    """True if we raised a conflict on a decoy that should stay quiet."""
    expected = gt.get("expected_scenes") or []
    gt_words = _norm(gt.get("description", ""))
    if str(gt.get("type", "")).startswith("legal") or gt.get("type") == "not_a_flag":
        for f in report.clearance_flags:
            if expected and not _overlap(expected, [f.scene_id]):
                continue
            blob = _norm(f"{f.reference_text} {f.risk_note}")
            if expected or (gt_words and len(gt_words & blob) >= 2):
                return True
        return False
    for c in report.conflicts:
        if expected and _overlap(expected, c.source_scene_ids):
            return True
        blob = _norm(f"{c.summary} {c.explanation}")
        if gt_words and len(gt_words & blob) >= 3:
            return True
    return False


def score_report(report: ContinuityReport, ground_truth: list[dict]) -> dict:
    planted = [gt for gt in ground_truth if gt.get("type") in PLANTED_TYPES]
    decoys = [gt for gt in ground_truth if gt.get("type") in DECOY_TYPES]
    other = [gt for gt in ground_truth if gt not in planted and gt not in decoys]

    hits = []
    misses = []
    for gt in planted:
        matched = _conflict_matches_gt(gt, report)
        row = {"type": gt.get("type"), "description": gt.get("description"), "matched": matched}
        (hits if matched else misses).append(row)

    false_alarms = []
    for gt in decoys:
        if _decoy_was_flagged(gt, report):
            false_alarms.append({"type": gt.get("type"), "description": gt.get("description")})

    recall = len(hits) / len(planted) if planted else None
    return {
        "planted": len(planted),
        "detected": len(hits),
        "missed": misses,
        "hits": hits,
        "decoys": len(decoys),
        "false_alarms_on_decoys": false_alarms,
        "recall": recall,
        "unscored_entries": other,
        "live_conflicts": len(report.conflicts),
        "live_legal_flags": len(report.clearance_flags),
        "analysis_source": report.analysis_source,
    }
