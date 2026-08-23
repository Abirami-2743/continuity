"""
Comparator Agent.

Design: pure "ask an LLM if two scenes conflict" is weak — it re-reads raw
text every time and has no memory. Instead:

  1. DETERMINISTIC step: scan the accumulated story-state for entities
     (characters/props) that recur across 2+ scenes with differing
     attributes. This is plain Python, not an LLM call — it's what makes
     the system auditable.
  2. LLM REASONING step: for each entity, send its FULL scene history in
     ONE call (not one call per pair) and ask the model to find every
     genuine issue across that timeline at once.

Why one call per entity instead of one call per pair: with N occurrences
of an entity, comparing every pair is O(N^2) calls, and each call repeats
the full system prompt — that repeated overhead is what actually burns
through a token budget fastest, not the scene content itself. One call
per entity is O(N) calls total, pays the system-prompt cost once per
entity, and lets the model reason across the WHOLE timeline instead of
two scenes in isolation (which is also better reasoning, not just cheaper
— e.g. catching a 3-scene pattern a single pairwise comparison would miss).

Nothing here is hardcoded per-story: the entity groupings are generated
from whatever SceneFacts actually exist, and the judgment call is a real
model call per entity.
"""
import uuid
from concurrent.futures import ThreadPoolExecutor
from app.llm import call_json
from app.models.schema import SceneFacts, ConflictFlag, ConflictType, Severity

MAX_PARALLEL_CALLS = 3  # entity count is usually much smaller than old pair count, can afford a bit more concurrency

JUDGE_SYSTEM_PROMPT = """You are the Comparator Agent in a script-continuity
system. You are given ONE entity (a character or prop) and EVERY scene in
which it appears, in chronological order. Find every genuine continuity
issue across this entity's full history — do not limit yourself to
comparing just two scenes at a time; look across the whole timeline for
patterns (e.g. a value that changes back and forth, or a 3-scene chain
where the middle scene explains what would otherwise look like a jump).

Return ONLY a JSON object:
{
  "conflicts": [
    {
      "conflict_type": "contradiction"|"state_violation"|"unresolved_thread",
      "severity": "high"|"medium"|"low",
      "summary": str,          // one short line, e.g. "Weather contradiction"
      "explanation": str,      // why this is a continuity error
      "confidence": float,     // 0.0-1.0
      "scene_ids": [str, ...]  // the specific scenes this issue spans (2+)
    }
  ]
}
Return an empty "conflicts" list if there are no genuine issues. Multiple
distinct issues for the same entity are fine — return each separately.

Rules:
- "contradiction": the same event/moment is described with incompatible
  facts (e.g. same flashback scene, weather differs).
- "state_violation": an established state (dead, destroyed, lost) changes
  without any explanation given anywhere in the entity's scene history.
- A costume change between DIFFERENT days/scenes is normal, not a conflict
  — only flag if it's implausible given the context (e.g. same explicit
  moment, or an object stated destroyed then intact with no explanation).
- IMPORTANT EXCEPTION: if any scene's raw text specifically calls out an
  item as newly acquired, notable, or significant (e.g. "just bought",
  "brand new", a gift, a family heirloom), that item's disappearance or
  replacement in a later scene with NO explanation IS a real contradiction,
  even across different days — ordinary daily variation does not apply to
  an item the story itself flagged as significant. Read the raw text of
  every scene, not just the extracted attributes, before deciding.
- An item or object changing hands (owner field differs) is NOT a conflict
  if any scene's raw text explicitly narrates the handoff (e.g. "hands the
  pouch to", "gives it to", "delivers it to"). Only flag ownership/custody
  changes that have NO narrated transfer anywhere in the whole history —
  that's when an item silently moved with no story explanation.
- Explained changes (a coworker mentions an accident, a character says
  "I got a haircut") are NOT conflicts. Only flag genuinely unexplained
  changes, checking every scene's raw text for an explanation first.
- If there's clearly no issue, return an empty conflicts list.
"""


def _merge_near_duplicate_names(
    by_name: dict[str, list[tuple[SceneFacts, dict]]]
) -> dict[str, list[tuple[SceneFacts, dict]]]:
    """The Extractor reads each scene independently, so it has no memory of
    what it called something in an earlier scene — 'ring' in one scene and
    'gold ring' in another are the same object, but arrive as different
    keys. Merge any two same-type entities where one name's words are fully
    contained in the other's (e.g. {'ring'} is a subset of {'gold','ring'})
    — deterministic word-overlap, not an LLM call, so it's auditable and
    won't accidentally merge unrelated things like 'ring' and 'earring'
    (different words entirely, no subset relationship)."""
    keys = list(by_name.keys())
    parent = {k: k for k in keys}

    def find(k: str) -> str:
        while parent[k] != k:
            k = parent[k]
        return k

    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            type1, name1 = keys[i].split(":", 1)
            type2, name2 = keys[j].split(":", 1)
            if type1 != type2:
                continue
            words1, words2 = set(name1.split()), set(name2.split())
            if words1 and words2 and (words1 <= words2 or words2 <= words1):
                # merge into whichever name has more words — the more
                # specific/descriptive one becomes the canonical label
                bigger = keys[i] if len(words1) >= len(words2) else keys[j]
                smaller = keys[j] if bigger == keys[i] else keys[i]
                parent[find(smaller)] = find(bigger)

    merged: dict[str, list[tuple[SceneFacts, dict]]] = {}
    for k in keys:
        merged.setdefault(find(k), []).extend(by_name[k])
    return merged


def _group_by_entity(all_facts: list[SceneFacts]) -> dict[str, list[SceneFacts]]:
    """Deterministic step: group full SceneFacts by every recurring
    character/prop name (after merging near-duplicate names — see above),
    keeping only entities with 2+ occurrences AND at least one differing
    attribute across them (otherwise there's nothing to compare — the
    entity is just present, unchanged, everywhere)."""
    by_name: dict[str, list[tuple[SceneFacts, dict]]] = {}
    for facts in all_facts:
        for c in facts.characters:
            by_name.setdefault(f"character:{c.name.lower()}", []).append((facts, c.model_dump()))
        for p in facts.props:
            by_name.setdefault(f"prop:{p.name.lower()}", []).append((facts, p.model_dump()))

    by_name = _merge_near_duplicate_names(by_name)

    grouped: dict[str, list[SceneFacts]] = {}
    for entity_name, occurrences in by_name.items():
        if len(occurrences) < 2:
            continue
        comparable_keys = [k for k in occurrences[0][1] if k != "name"]
        has_variation = False
        for i in range(len(occurrences)):
            for j in range(i + 1, len(occurrences)):
                _, attrs_a = occurrences[i]
                _, attrs_b = occurrences[j]
                if any(attrs_a.get(k) not in (None, "unknown") and
                       attrs_b.get(k) not in (None, "unknown") and
                       attrs_a.get(k) != attrs_b.get(k)
                       for k in comparable_keys):
                    has_variation = True
                    break
            if has_variation:
                break
        if has_variation:
            # sort chronologically by scene_index — merging can interleave
            # scenes from what were originally two separate name-groups
            scenes = sorted((facts for facts, _ in occurrences), key=lambda f: f.scene_index)
            grouped[entity_name] = scenes

    return grouped


def compare_story_state(all_facts: list[SceneFacts]) -> list[ConflictFlag]:
    entity_groups = _group_by_entity(all_facts)

    def judge_entity(item: tuple[str, list[SceneFacts]]) -> list[ConflictFlag]:
        entity_name, scenes = item
        clean_name = entity_name.split(":", 1)[-1]  # "character:daniel" -> "daniel"

        scenes_block = "\n\n".join(
            f"SCENE {s.scene_id} FACTS:\n{s.model_dump_json()}" for s in scenes
        )
        user_prompt = f"ENTITY: {clean_name}\n\n{scenes_block}"

        result = call_json(system_prompt=JUDGE_SYSTEM_PROMPT, user_prompt=user_prompt)
        flags = []
        for c in result.get("conflicts", []):
            flags.append(ConflictFlag(
                conflict_id=f"CONTINUITY-{uuid.uuid4().hex[:6].upper()}",
                conflict_type=ConflictType(c["conflict_type"]),
                severity=Severity(c["severity"]),
                entity_name=clean_name,
                summary=c["summary"],
                explanation=c["explanation"],
                source_scene_ids=c["scene_ids"],
                confidence=float(c["confidence"]),
            ))
        return flags

    if not entity_groups:
        return []

    with ThreadPoolExecutor(max_workers=MAX_PARALLEL_CALLS) as pool:
        results = pool.map(judge_entity, entity_groups.items())

    all_flags = [flag for flags in results for flag in flags]
    return all_flags