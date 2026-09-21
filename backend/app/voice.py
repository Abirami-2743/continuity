"""
Voice narration of the Supervisor Agent's report summary via gTTS
(Google Text-to-Speech). This is a genuine product feature (played from
the dashboard), not just video-narration tooling — see README for the
distinction and why it's scoped this way.

Originally built on ElevenLabs, swapped to gTTS because the team doesn't
have a paid/free ElevenLabs quota available for the hackathon build.
gTTS is free, needs no API key, and returns MP3 bytes just like the old
implementation did — so main.py's /narrate endpoint and the frontend's
audio-fetching code didn't need to change at all.
"""
import io

from gtts import gTTS
from gtts.tts import gTTSError

DEFAULT_LANG = "en"


def narrate(text: str, lang: str = DEFAULT_LANG) -> bytes:
    """Returns raw MP3 bytes for the given text.

    Raises RuntimeError if synthesis fails (e.g. no network access to
    Google's TTS endpoint) — no fallback fake audio, matching the old
    ElevenLabs behavior of failing loudly rather than silently.
    """
    if not text or not text.strip():
        raise RuntimeError("Cannot narrate empty text.")

    try:
        tts = gTTS(text=text, lang=lang)
        buf = io.BytesIO()
        tts.write_to_fp(buf)
        return buf.getvalue()
    except gTTSError as e:
        raise RuntimeError(f"gTTS synthesis failed: {e}") from e