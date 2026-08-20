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
from app.models.schema import SceneFacts

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
"""


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
        characters=result.get("characters", []),
        props=result.get("props", []),
        setting=result.get("setting"),
        weather=result.get("weather"),
        timeline_markers=result.get("timeline_markers", []),
        real_world_references=result.get("real_world_references", []),
    )