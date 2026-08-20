"""
Thin wrapper around the Groq API. Every agent calls through THIS module —
no agent is allowed to hardcode a response or fake a completion. If
GROQ_API_KEY is missing, calls fail loudly (no silent mock fallback),
because a hackathon judge or reviewer re-running this code should see a
real error, not a fabricated success.
"""
import os
import json
import re
import time
from pathlib import Path
from dotenv import load_dotenv
from groq import Groq, APIConnectionError, APIStatusError, RateLimitError

# Explicit path — don't rely on load_dotenv()'s auto-search, which can miss
# the file depending on how the script was invoked (e.g. `python -m app.eval`
# vs `python app/eval.py`). backend/.env is always two levels up from here.
_ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=_ENV_PATH)

MODEL = "openai/gpt-oss-120b"       # stronger reasoning — used by Comparator, Legal Clearance
FAST_MODEL = "openai/gpt-oss-20b"  # smaller/faster — used by Extractor, which is simpler structured pulling
MAX_RETRIES = 4

_client: Groq | None = None


def get_client() -> Groq:
    global _client
    if _client is None:
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError(
                f"GROQ_API_KEY is not set. Looked for .env at: {_ENV_PATH} "
                f"(exists: {_ENV_PATH.exists()}). Continuity calls the real "
                f"Groq API for every agent — set the env var before running."
            )
        _client = Groq(api_key=api_key)
    return _client


def _parse_retry_seconds(message: str, fallback: float) -> float:
    """Groq's 429 error message includes the exact wait time, e.g.
    'Please try again in 7.1099999s' — use that instead of guessing with
    a generic backoff, since it's more accurate and often much shorter."""
    match = re.search(r"try again in ([\d.]+)s", message)
    if match:
        return float(match.group(1)) + 0.5  # small buffer
    return fallback


def call_json(system_prompt: str, user_prompt: str, temperature: float = 0.1,
              model: str = MODEL) -> dict:
    """Call Groq with JSON-mode enforced structured output. Returns a parsed
    dict. Retries on transient network errors AND rate limits (free-tier
    tokens-per-minute caps are easy to hit once calls run concurrently) —
    but still raises for real failures (bad key, malformed JSON, persistent
    failure) rather than swallowing them or returning fake data.

    `model` defaults to the stronger MODEL, but callers doing simpler
    structured-extraction work (not nuanced judgment) can pass FAST_MODEL —
    this spreads load across two separate per-model rate-limit budgets on
    Groq's free tier, instead of every agent competing for the same one."""
    client = get_client()
    last_error = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = client.chat.completions.create(
                model=model,
                temperature=temperature,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
            content = response.choices[0].message.content
            return json.loads(content)
        except RateLimitError as e:
            last_error = e
            if attempt < MAX_RETRIES:
                wait = _parse_retry_seconds(str(e), fallback=2 ** attempt * 3)
                print(f"  [retry {attempt}/{MAX_RETRIES}] rate limited, "
                      f"waiting {wait:.1f}s...")
                time.sleep(wait)
        except (APIConnectionError, json.JSONDecodeError) as e:
            last_error = e
            if attempt < MAX_RETRIES:
                wait = 2 ** attempt  # 2s, 4s, 8s, 16s
                print(f"  [retry {attempt}/{MAX_RETRIES}] {type(e).__name__}, "
                      f"retrying in {wait}s...")
                time.sleep(wait)
        except APIStatusError:
            raise  # real API errors (bad model, bad key) — don't retry blindly

    raise last_error
