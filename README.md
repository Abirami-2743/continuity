# Continuity — Script Continuity & Legal Clearance Agent

Multi-agent system (Extractor → Comparator → Legal Clearance → Supervisor)
that reads a set of script scenes, builds a structured story-state, and
flags continuity contradictions, state violations, unresolved threads, and
legal clearance risks — with every flag traceable back to its exact source
scenes and a confidence score. Built for The Great Agent Hackathon, Track 3
(AI-native Enterprise, open stack).

## What's real here (important for review)

- **No hardcoded agent outputs.** Every extraction, comparison judgment,
  and clearance flag is a live call to the Groq API (`app/llm.py`,
  `app/agents/*.py`). There is no fallback that fabricates a result if the
  API key is missing — calls fail loudly instead.
- **Comparator is not just "ask the LLM if two scenes conflict."** It first
  deterministically finds candidate entity pairs across the accumulated
  story-state (`_entity_candidates` in `comparator.py`), then asks the LLM
  to judge only real candidates. This is auditable — you can see exactly
  why a pair was even considered.
- **Supervisor is an actual LangGraph state graph** (`supervisor.py`), not
  a sequence of plain function calls dressed up as "agents."
- **Frontend renders real data.** The Story Timeline component reads
  `report.scene_facts` — the Extractor's literal structured output — not a
  client-side reconstruction or parsed summary text.
- **Ground-truth eval set** (`data/sample_scripts/maya_demo.json`) has
  known planted inconsistencies with an answer key, so detection can be
  measured (`python -m app.eval`) instead of eyeballed.

## What's a stretch feature, scoped honestly

- **ElevenLabs voice narration** (`app/voice.py`, `GET
  /api/reports/{id}/narrate`) is a real product feature — the Supervisor's
  summary text is sent to ElevenLabs and played from the dashboard — not
  just used for video-narration. If `ELEVENLABS_API_KEY` is unset, the
  endpoint fails cleanly; the rest of the app is unaffected.
- **Parallel API enrichment** (`app/parallel_search.py`) is an optional
  hook for the Legal Clearance agent to verify a real-world reference
  before reasoning about it. It's not yet wired into
  `legal_clearance.py` by default — safe to skip if you don't have a key
  and want fewer moving parts during the demo.

## Setup

### Backend
```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

export GROQ_API_KEY=your_key
export MONGODB_URI=mongodb://localhost:27017   # or your Atlas URI
export ELEVENLABS_API_KEY=your_key             # optional, for narration

uvicorn app.main:app --reload --port 8000
```

### Run the eval against the ground-truth demo set
```bash
python -m app.eval
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```
Opens on `http://localhost:5173`, proxies `/api` to `localhost:8000`.

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
       │   AGENT   │      (MongoDB)      │    AGENT     │
       └─────┬─────┘                     └──────┬───────┘
             │                                   │
             ▼                                   │
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

## Not yet built (be upfront about this in the demo/submission)

- Auth / multi-user accounts — out of scope for Stage 1
- PDF script upload parsing — currently takes plain-text scenes; a PDF ->
  text step is a small addition (`pdfplumber` or similar) if time allows
- Automated ground-truth grading in `eval.py` — currently prints both
  sides for manual comparison, doesn't auto-score
