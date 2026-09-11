"""
Voice narration of the Supervisor Agent's report summary via ElevenLabs.
This is a genuine product feature (played from the dashboard), not just
video-narration tooling — see README for the distinction and why it's
scoped this way.
"""
import os
import requests

ELEVENLABS_TTS_URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
DEFAULT_VOICE_ID = "21m00Tcm4TlvDq8ikWAM"  # ElevenLabs default "Rachel" voice


def narrate(text: str, voice_id: str = DEFAULT_VOICE_ID) -> bytes:
    """Returns raw MP3 bytes for the given text. Raises if ELEVENLABS_API_KEY
    is unset or the request fails — no fallback fake audio."""
    api_key = os.environ.get("ELEVENLABS_API_KEY")
    if not api_key:
        raise RuntimeError("ELEVENLABS_API_KEY is not set.")

    response = requests.post(
        ELEVENLABS_TTS_URL.format(voice_id=voice_id),
        headers={
            "xi-api-key": api_key,
            "Content-Type": "application/json",
        },
        json={
            "text": text,
            "model_id": "eleven_flash_v2_5",  # eleven_monolingual_v1 was
                                                # deprecated & removed by
                                                # ElevenLabs on 2026-07-09 —
                                                # this is their current
                                                # low-latency recommendation
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
        },
        timeout=30,
    )
    if not response.ok:
        # Surface ElevenLabs' actual error body instead of a bare status
        # code — this is what would have told us "model deprecated"
        # immediately instead of needing a web search to find out.
        raise RuntimeError(
            f"ElevenLabs TTS failed ({response.status_code}): {response.text}"
        )
    return response.content