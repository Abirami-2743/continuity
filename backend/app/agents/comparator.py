"""
Comparator Agent.

Design: pure "ask an LLM if two scenes conflict" is weak — it re-reads raw
text every time and has no memory. Instead:

  1. DETERMINISTIC step: scan the accumulated story-state for entities
     (characters/props) that recur across scenes, and build candidate pairs
     where the same named entity has DIFFERENT recorded attributes. This is
     plain Python, not an LLM call — it's what makes the system auditable.
  2. LLM REASONING step: for each candidate pair, ask the model to judge
     whether this is a genuine contradiction, a state violation, or just an
     explainable change (e.g. a costume change *within* the same day isn't
     necessarily a continuity error) — and to produce severity + confidence.

Nothing here is hardcoded per-story: the candidate pairs are generated from
whatever SceneFacts actually exist, and the judgment call is a real model
call per candidate.
"""
import uuid
from concurrent.futures import ThreadPoolExecutor
from app.llm import call_json
from app.models.schema import SceneFacts, ConflictFlag, ConflictType, Severity

MAX_PARALLEL_CALLS = 2  # matches supervisor.py -- lowered after hitting real TPM rate limits at 5

JUDGE_SYSTEM_PROMPT = """You are the Comparator Agent in a script-continuity
system. You are given two scenes' extracted facts about the SAME named
character or prop, drawn from different points in a script/series. Decide
whether this represents a genuine continuity issue.

Return ONLY a JSON object:
{
  "is_conflict": bool,
  "conflict_type": "contradiction"|"state_violation"|"unresolved_thread",
  "severity": "high"|"medium"|"low",
  "summary": str,          // one short line, e.g. "Weather contradiction"
  "explanation": str,      // why this is/isn't a continuity error
  "confidence": float      // 0.0-1.0
}

Rules:
- "contradiction": the same event/moment is described with incompatible
  facts (e.g. same flashback scene, weather differs).
- "state_violation": an established state (dead, destroyed, lost) changes
  without any explanation given in either scene.
- A costume change between DIFFERENT days/scenes is normal, not a conflict
  — only flag if it's implausible given the context (e.g. same explicit
  moment, or an object stated destroyed then intact with no explanation).
- IMPORTANT EXCEPTION: if either scene's raw text specifically calls out an
  item as newly acquired, notable, or significant (e.g. "just bought",
  "brand new", a gift, a family heirloom), that item's disappearance or
  replacement in a later scene with NO explanation IS a real contradiction,
  even across different days — ordinary daily variation does not apply to
  an item the story itself flagged as significant. Read both scenes' full
  raw text, not just the extracted attributes, before deciding.
- An item or object changing hands (owner field differs) is NOT a conflict
  if the raw text of either scene explicitly narrates the handoff (e.g.
  "hands the pouch to", "gives it to", "delivers it to"). Only flag
  ownership/custody changes that have NO narrated transfer anywhere —
  that's when an item silently moved with no story explanation.
- Explained changes (a coworker mentions an accident, a character says
  "I got a haircut") are NOT conflicts. Only flag genuinely unexplained
  changes, and check both scenes' raw text for an explanation before
  concluding something is unexplained.
- If it's clearly not an issue, set is_conflict to false.
"""


def _entity_candidates(all_facts: list[SceneFacts]) -> list[tuple[str, SceneFacts, SceneFacts]]:
    """Deterministic step: find recurring character/prop names across
    scenes and pair up scenes where recorded attributes differ."""
    by_name: dict[str, list[tuple[SceneFacts, dict]]] = {}
    for facts in all_facts:
        for c in facts.characters:
            by_name.setdefault(f"character:{c.name.lower()}", []).append((facts, c.model_dump()))
        for p in facts.props:
            by_name.setdefault(f"prop:{p.name.lower()}", []).append((facts, p.model_dump()))

    candidates = []
    for entity_name, occurrences in by_name.items():
        if len(occurrences) < 2:
            continue
        for i in range(len(occurrences)):
            for j in range(i + 1, len(occurrences)):
                scene_a, attrs_a = occurrences[i]
                scene_b, attrs_b = occurrences[j]
                # only a candidate if some attribute actually differs
                comparable_keys = [k for k in attrs_a if k not in ("name",)]
                if any(attrs_a.get(k) not in (None, "unknown") and
                       attrs_b.get(k) not in (None, "unknown") and
                       attrs_a.get(k) != attrs_b.get(k)
                       for k in comparable_keys):
                    candidates.append((entity_name, scene_a, scene_b))
    return candidates


def compare_story_state(all_facts: list[SceneFacts]) -> list[ConflictFlag]:
    candidates = _entity_candidates(all_facts)

    def judge(candidate: tuple[str, SceneFacts, SceneFacts]) -> tuple[str, ConflictFlag] | None:
        entity_name, scene_a, scene_b = candidate
        clean_name = entity_name.split(":", 1)[-1]  # "character:daniel" -> "daniel", matches display names
        user_prompt = (
            f"ENTITY: {entity_name}\n\n"
            f"SCENE {scene_a.scene_id} FACTS:\n{scene_a.model_dump_json()}\n\n"
            f"SCENE {scene_b.scene_id} FACTS:\n{scene_b.model_dump_json()}\n"
        )
        result = call_json(system_prompt=JUDGE_SYSTEM_PROMPT, user_prompt=user_prompt)
        if not result.get("is_conflict"):
            return None
        return (entity_name, ConflictFlag(
            conflict_id=f"CONTINUITY-{uuid.uuid4().hex[:6].upper()}",
            conflict_type=ConflictType(result["conflict_type"]),
            severity=Severity(result["severity"]),
            entity_name=clean_name,
            summary=result["summary"],
            explanation=result["explanation"],
            source_scene_ids=[scene_a.scene_id, scene_b.scene_id],
            confidence=float(result["confidence"]),
        ))

    # Each candidate pair's judgment is independent — run them concurrently
    # rather than one Groq call at a time, since this is often the slowest
    # step (candidate count grows with recurring entities x scenes).
    with ThreadPoolExecutor(max_workers=MAX_PARALLEL_CALLS) as pool:
        results = pool.map(judge, candidates)
    raw_flags = [r for r in results if r is not None]

    return _dedupe_flags(raw_flags)


_SEVERITY_RANK = {Severity.HIGH: 3, Severity.MEDIUM: 2, Severity.LOW: 1}


def _dedupe_flags(raw_flags: list[tuple[str, ConflictFlag]]) -> list[ConflictFlag]:
    """The same real-world issue (e.g. 'the locket') often surfaces across
    several scene-pairs, since every pair involving that entity gets judged
    independently. Merge flags that share the same entity + conflict_type
    into one, unioning their source scenes and keeping the highest severity
    and confidence seen — so one real story issue reads as one flag, not
    three or four near-duplicates."""
    grouped: dict[tuple[str, ConflictType], ConflictFlag] = {}

    for entity_name, flag in raw_flags:
        key = (entity_name, flag.conflict_type)
        if key not in grouped:
            grouped[key] = flag
            continue

        existing = grouped[key]
        merged_scenes = list(dict.fromkeys(existing.source_scene_ids + flag.source_scene_ids))
        best = existing if _SEVERITY_RANK[existing.severity] >= _SEVERITY_RANK[flag.severity] else flag
        grouped[key] = ConflictFlag(
            conflict_id=existing.conflict_id,
            conflict_type=existing.conflict_type,
            severity=best.severity,
            entity_name=existing.entity_name,
            summary=best.summary,
            explanation=best.explanation,
            source_scene_ids=merged_scenes,
            confidence=max(existing.confidence, flag.confidence),
        )

    return list(grouped.values())