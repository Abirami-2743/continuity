"""
Legal Clearance Agent.

Job: for every real_world_reference already pulled out by the Extractor
(real people, brands, copyrighted works), assess whether it poses a
clearance risk worth flagging for human/legal review. This is a real LLM
call reasoning about each reference in context — it never asserts a legal
conclusion, only "requires human review" plus a risk note. Continuity is
not a law firm; it surfaces evidence.

GROUNDING NOTE: `search_reference` (see parallel_search.py) is optional
live verification — it's a no-op returning None whenever PARALLEL_API_KEY
isn't set, in which case every judgment below is made from the model's
own training knowledge alone, with no way to actually confirm whether an
unfamiliar-but-plausible-sounding name is real. The prompt is written to
be honest about that uncertainty rather than defaulting to over-caution
on every plausible-sounding name (see the "worth_flagging" guidance).
"""
import uuid
from concurrent.futures import ThreadPoolExecutor
from app.llm import call_json
from app.models.schema import SceneFacts, ClearanceFlag, RealWorldReference
from app.parallel_search import search_reference

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
only note that human/legal review is warranted and why.

How to decide "worth_flagging", when no web verification snippets are
provided (or they don't resolve the question):
- If you have clear, confident general knowledge that this specific name
  refers to a real, identifiable person, brand, or copyrighted work (e.g.
  a widely known public figure, a well-known company/product, a famous
  film/book/show title used by its real title), flag it — your own
  knowledge is a legitimate basis, you don't need a search snippet to
  recognize something famous.
- If the name is merely plausible-sounding (e.g. a generic-sounding
  company or product name) and you do NOT have actual confirmation, from
  your own knowledge or the provided context, that it corresponds to a
  specific real-world entity, do NOT flag it purely because it sounds
  like it could be real. A name being unremarkable or realistic-sounding
  is not itself evidence of a clearance risk — most scripts invent
  plausible-sounding fictional names on purpose, and flagging every one
  of them defeats the point of this check. Only flag when you can
  articulate which specific real entity you believe this refers to.
- A brief, casual mention of a real, specifically-named work (e.g. a
  character comparing a situation to a well-known film by name) is still
  worth flagging — title usage itself is the kind of thing legal review
  exists to catch — but the risk_note should reflect that the usage is a
  passing reference, not a full portrayal, which is generally lower risk
  and should be reflected in a lower confidence than, say, prominently
  featuring a trademarked product on screen.
- Trivial, clearly-fictional (per the above), or non-identifying mentions
  should not be flagged.
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

    def judge(pair: tuple[SceneFacts, RealWorldReference]) -> ClearanceFlag | None:
        facts, ref = pair
        web_context = None
        try:
            web_context = search_reference(ref.reference_text)
        except Exception:
            web_context = None
        user_prompt = (
            f"SCENE CONTEXT: {facts.raw_text}\n\n"
            f"REFERENCE: \"{ref.reference_text}\" (type: {ref.reference_type})"
        )
        if web_context:
            user_prompt += (
                "\n\nOPTIONAL PUBLIC WEB SNIPPETS (may be incomplete; do not "
                f"treat as legal advice):\n{web_context}"
            )
        else:
            user_prompt += (
                "\n\nNo web verification is available for this reference — base "
                "your judgment on your own knowledge only, per the grounding "
                "guidance in your instructions."
            )
        result = call_json(system_prompt=SYSTEM_PROMPT, user_prompt=user_prompt)
        if not result.get("worth_flagging"):
            return None
        return ClearanceFlag(
            flag_id=f"LEGAL-{uuid.uuid4().hex[:6].upper()}",
            scene_id=facts.scene_id,
            reference_text=ref.reference_text,
            reference_type=ref.reference_type,
            risk_note=result.get("risk_note") or "Human legal review recommended.",
            confidence=float(result.get("confidence", 0.5)),
            web_context=web_context,
        )

    if not pairs:
        return []

    with ThreadPoolExecutor(max_workers=MAX_PARALLEL_CALLS) as pool:
        results = pool.map(judge, pairs)
    return [r for r in results if r is not None]