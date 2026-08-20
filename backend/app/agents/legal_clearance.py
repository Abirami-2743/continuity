"""
Legal Clearance Agent.

Job: for every real_world_reference already pulled out by the Extractor
(real people, brands, copyrighted works), assess whether it poses a
clearance risk worth flagging for human/legal review. This is a real LLM
call reasoning about each reference in context — it never asserts a legal
conclusion, only "requires human review" plus a risk note. Continuity is
not a law firm; it surfaces evidence.
"""
import uuid
from concurrent.futures import ThreadPoolExecutor
from app.llm import call_json
from app.models.schema import SceneFacts, ClearanceFlag

MAX_PARALLEL_CALLS = 2  # matches supervisor.py / comparator.py -- lowered after hitting real TPM rate limits at 5

SYSTEM_PROMPT = """You are the Legal Clearance Agent in a script-production
tool. You are given a real-world reference (a real person's name, a brand,
or a copyrighted work) as it's used in a scene. Assess clearance risk.

Return ONLY JSON:
{
  "worth_flagging": bool,
  "risk_note": str,     // plain-language note on why this might need clearance
  "confidence": float   // 0.0-1.0
}

You are NOT a lawyer and must never claim a definitive legal conclusion —
only note that human/legal review is warranted and why. Trivial, clearly
fictional, or non-identifying mentions should not be flagged.
"""


def clear_references(all_facts: list[SceneFacts]) -> list[ClearanceFlag]:
    # Flatten (scene, reference) pairs first so every reference across every
    # scene can be judged concurrently, instead of nested loops calling
    # Groq one at a time.
    pairs = [
        (facts, ref)
        for facts in all_facts
        for ref in facts.real_world_references
    ]

    def judge(pair: tuple[SceneFacts, "RealWorldReference"]) -> ClearanceFlag | None:
        facts, ref = pair
        user_prompt = (
            f"SCENE CONTEXT: {facts.raw_text}\n\n"
            f"REFERENCE: \"{ref.reference_text}\" (type: {ref.reference_type})"
        )
        result = call_json(system_prompt=SYSTEM_PROMPT, user_prompt=user_prompt)
        if not result.get("worth_flagging"):
            return None
        return ClearanceFlag(
            flag_id=f"LEGAL-{uuid.uuid4().hex[:6].upper()}",
            scene_id=facts.scene_id,
            reference_text=ref.reference_text,
            reference_type=ref.reference_type,
            risk_note=result["risk_note"],
            confidence=float(result["confidence"]),
        )

    if not pairs:
        return []

    with ThreadPoolExecutor(max_workers=MAX_PARALLEL_CALLS) as pool:
        results = pool.map(judge, pairs)
    return [r for r in results if r is not None]