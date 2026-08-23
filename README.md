# Continuity — Script Continuity & Legal Clearance Agent

Multi-agent system (Extractor → Comparator → Legal Clearance → Supervisor)
that reads a set of script scenes, builds a structured story-state, and
flags continuity contradictions, state violations, unresolved threads, and
legal clearance risks — with every flag traceable back to its exact source
scenes and a confidence score. Built for The Great Agent Hackathon, Track 3
(AI-native Enterprise, open stack).

Live repo: https://github.com/Abirami-2743/continuity

## What's real here (important for review)

- **No hardcoded agent outputs.** Every extraction, comparison judgment,
  and clearance flag is a live call to the Groq API (`app/llm.py`,
  `app/agents/*.py`). There is no fallback that fabricates a result if the
  API key is missing — calls fail loudly instead.
- **Comparator reasons across an entity's FULL scene history in one call**,
  not just two scenes at a time (`_group_by_entity` in `comparator.py`).
  Earlier iterations compared every pair of scenes separately — this was
  redesigned after real testing showed it burned through free-tier token
  budgets fast (repeated system-prompt overhead per pair) and missed
  multi-scene patterns a pairwise comparison can't see (e.g. a claim in
  scene 4 contradicted by a reveal in scene 8).
- **Near-duplicate entity names are merged**, both on the backend
  (`_merge_near_duplicate_names` in `comparator.py`) and in the frontend's
  Story Timeline (`mergeNearDuplicateRows` in `StoryTimeline.jsx`) — the
  Extractor reads each scene independently, so "ring" in one scene and
  "gold ring" in another arrive as different names for the same object.
  Merged via word-subset matching (word-boundary safe — "ring" merges into
  "gold ring" but not into "earring").
- **Two-model setup for cost/speed**: `openai/gpt-oss-120b` handles
  Comparator and Legal Clearance (nuanced judgment); `openai/gpt-oss-20b`
  handles Extraction (simpler structured pulling). Splits load across two
  separate Groq rate-limit budgets instead of one model competing with
  itself. If the stronger model hits its **daily** token cap specifically,
  `call_json` automatically falls back to the faster model for that call
  rather than retrying uselessly against a limit that can't reset in
  seconds (`llm.py`).
- **Retries with backoff on transient failures** (network drops, per-minute
  rate limits) — up to 4 attempts, reading Groq's own suggested wait time
  from the error when available.
- **Supervisor is an actual LangGraph state graph** (`supervisor.py`).
  Extractor runs once; Comparator and Legal Clearance branch off it in
  parallel. Each node returns only the state keys it changed (not the
  full state) — returning full state from parallel branches causes
  LangGraph to see conflicting writes to unchanged keys in the same step.
- **Frontend renders real data.** The Story Timeline component reads
  `report.scene_facts` — the Extractor's literal structured output — not a
  client-side reconstruction or parsed summary text.
- **MongoDB persistence is real and confirmed working** (Atlas free tier).
  Optional by design: if unreachable, `/api/analyze` logs a warning and
  still returns the live report instead of failing the request.
- **Six demo scripts across difficulty**, each with a ground-truth answer
  key: `weather_easy`, `maya_demo` (medium), `chain_of_custody_hard`,
  `decoys_very_hard` (tests false-positive avoidance, not just detection),
  `legal_precision` (tests judgment vs. keyword-matching), plus ad-hoc
  scripts written during testing (e.g. "The Understudy") that caught real
  bugs — see below.

## Bugs found and fixed through real testing (not glossed over)

This list is deliberately kept — it's evidence the system was actually
run and stress-tested, not just written and assumed to work:

- Comparator's rule against flagging ordinary costume changes was
  over-applying to a specifically-notable item (a "just bought" jacket) —
  tightened the judge prompt with an explicit exception.
- Object handoffs explicitly narrated in the story ("hands the pouch to")
  were being flagged as ownership violations — added a rule so narrated
  transfers aren't mistaken for silent, unexplained custody breaks.
- Story Timeline was cross-matching conflict flags onto unrelated rows
  whenever they shared a scene number — fixed by attaching `entity_name`
  to `ConflictFlag` end-to-end (schema → backend → frontend) so the UI
  can match on the actual entity, not just scene overlap.
- LangGraph `InvalidUpdateError` from parallel branches returning full
  state instead of partial deltas — see Supervisor note above.
- Groq model deprecation (`llama-3.3-70b-versatile` retired mid-project),
  an `httpx`/`groq` version conflict, and free-tier rate limits (both
  per-minute and per-day) — all hit live, all diagnosed and fixed rather
  than worked around by disabling functionality.

## What's a stretch feature, scoped honestly

- **ElevenLabs voice narration** (`app/voice.py`, `POST /api/narrate`) —
  code is written and the dashboard button exists, but **has not yet been
  tested with a real API key**. `ELEVENLABS_API_KEY` is currently unset;
  until it's added and verified, treat this as built-but-unconfirmed, not
  working. If unset, the endpoint fails cleanly and the rest of the app
  is unaffected.
- **Parallel API enrichment** (`app/parallel_search.py`) is an optional
  hook for the Legal Clearance agent to verify a real-world reference
  before reasoning about it. Not wired into `legal_clearance.py` by
  default — safe to skip if you don't have a key.

## Setup

### Backend
```bash
cd backend
python -m venv venv && source venv/bin/activate    # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Create backend/.env with:
GROQ_API_KEY=your_key
MONGODB_URI=your_mongodb_atlas_uri    # optional — falls back gracefully if unset/unreachable
ELEVENLABS_API_KEY=                   # optional, unverified feature — see above
PARALLEL_API_KEY=                     # optional, unused by default

uvicorn app.main:app --reload --port 8000
```

### Check which models your Groq key actually has access to
```bash
python list_models.py
```
Don't assume a model name from docs or memory is available on your
account — this project hit two real 404s from models that looked valid
elsewhere but weren't accessible on the account in use.

### Run the eval against any ground-truth demo set
```bash
python -m app.eval                        # defaults to maya_demo
python -m app.eval weather_easy
python -m app.eval decoys_very_hard        # the one that tests false positives, not just detection
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```
Opens on `http://localhost:5173`, proxies `/api` to `localhost:8000`. The
"Demo set" dropdown loads any of the 6 difficulty-ranked scripts directly
from `public/sample_scripts/`.

## Architecture

```
                    ┌──────────────────┐
                    │    SUPERVISOR    │  (LangGraph state graph)
                    └────────┬─────────┘
                             │
             ┌───────────────┼────────────────┐
             ▼                                 ▼
       ┌───────────┐                     ┌──────────────┐
       │ EXTRACTOR │──▶ story-state ────▶│  COMPARATOR  │
       │  (fast    │      (MongoDB,      │  (reasons    │
       │  model)   │       optional)     │  per-entity, │
       └─────┬─────┘                     │  full history│
             │                           │  in 1 call)  │
             ▼                           └──────┬───────┘
       ┌──────────────┐                          │
       │    LEGAL     │                          │
       │  CLEARANCE   │                          │
       └──────┬───────┘                          │
              │                                  │
              └────────────────┬─────────────────┘
                                ▼
                     ┌───────────────────┐
                     │ CONTINUITY REPORT │
                     │ conflicts, flags, │
                     │ confidence, voice │
                     └───────────────────┘
```

## Not yet built

- Auth / multi-user accounts — out of scope for Stage 1
- PDF script upload parsing — currently takes plain-text scenes only
- Deployment — runs locally only; no live URL yet (not required for
  Stage 1, which accepts a video demo of a working local build)
- Automated ground-truth grading in `eval.py` — currently prints both
  sides for manual comparison, doesn't auto-score
- ElevenLabs narration verified end-to-end — see stretch features above