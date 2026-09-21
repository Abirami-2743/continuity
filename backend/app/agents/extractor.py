"""
Extractor Agent.

Job: read ONE scene of raw script text and produce structured SceneFacts
(characters, props, setting, weather, timeline markers, real-world
references). This is a real LLM call against the scene text — the model
decides what's present in the scene; nothing here is templated per-scene
or pre-written. Different scripts produce genuinely different extractions.
"""
import uuid
from app.llm import call_json, FAST_MODEL
from app.models.schema import SceneFacts, Character, Prop, TimelineMarker, RealWorldReference

SYSTEM_PROMPT = """You are the Extractor Agent in a script-continuity system.
Read the given scene and extract structured facts. Return ONLY a JSON object
with this exact shape:

{
  "characters": [{"name": str, "status": "alive"|"dead"|"unknown",
                   "appearance": str|null, "location": str|null}],
  "props": [{"name": str, "state": "present"|"lost"|"destroyed"|"possessed"|"unknown",
             "owner": str|null}],
  "setting": str|null,
  "weather": str|null,
  "timeline_markers": [{"description": str, "relative_time": str|null}],
  "real_world_references": [{"reference_text": str,
                               "reference_type": "person"|"brand"|"copyrighted_work"|"other"}]
}

Only include what is actually stated or strongly implied in the scene text.
Do not invent details. If a field has nothing relevant, use an empty list
or null. Be precise about appearance and prop state — these are the details
a continuity error would violate later in the story.

For "real_world_references": capture every mention of a specific real
person, brand/product, or copyrighted work (film, book, show, song, etc.),
by its real name — including INDIRECT or CASUAL mentions, not just when a
character directly interacts with the thing. This includes:
- A character comparing the current situation to a named real film, show,
  book, or other work ("this feels like X", "it's like something out of Y",
  "reminds me of Z").
- A character name-dropping a real person in passing dialogue, even
  without meeting them (e.g. mentioning having met them, admiring them,
  quoting them).
- A real brand or product mentioned by name, even briefly or in the
  background, not just when it's a plot-relevant object.
A reference does not need to be central to the scene to count — a single
passing line is enough. Only skip references to clearly invented, fictional
names that the story itself created (e.g. an in-universe company or
product with no real-world counterpart).
"""


def _parse_many(model, items):
    parsed = []
    for item in items or []:
        try:
            parsed.append(model.model_validate(item))
        except Exception:
            continue
    return parsed


def extract_scene(script_id: str, scene_index: int, raw_text: str) -> SceneFacts:
    scene_id = f"{script_id}-scene-{scene_index}"
    result = call_json(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=f"SCENE TEXT:\n\n{raw_text}",
        model=FAST_MODEL,  # extraction is structured pulling, not nuanced
                            # judgment — a smaller/faster model handles it
                            # well, and frees up gpt-oss-120b's budget for
                            # the harder Comparator/Legal reasoning calls
    )
    return SceneFacts(
        script_id=script_id,
        scene_id=scene_id,
        scene_index=scene_index,
        raw_text=raw_text,
        characters=_parse_many(Character, result.get("characters")),
        props=_parse_many(Prop, result.get("props")),
        setting=result.get("setting"),
        weather=result.get("weather"),
        timeline_markers=_parse_many(TimelineMarker, result.get("timeline_markers")),
        real_world_references=_parse_many(RealWorldReference, result.get("real_world_references")),
    )