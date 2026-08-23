# Continuity

**Continuity gives your story a memory.**

A multi-agent system that reads a script's scenes and flags continuity errors — a character's appearance that contradicts an earlier scene, an object that vanishes and reappears with no explanation, a claim one scene makes that a later scene quietly contradicts — plus legal clearance risks like real people, brands, or copyrighted references. Every flag is evidence for a human to review, not an automated verdict.

Built for **The Great Agent Hackathon** (Track 3: AI-native Enterprise, open stack).

---

## The problem

Even large, well-resourced productions ship continuity errors — because checking consistency across hundreds of pages, multiple drafts, and dozens of scenes currently depends on a human's memory. Continuity turns that manual check into a systematic, auditable one.

## How it works

Four agents, each with one job:

| Agent | Job |
|---|---|
| **Extractor** | Reads each scene, pulls out structured facts — who's there, what they look like, what state props are in, any real-world references |
| **Comparator** | Reasons across each character/prop's *entire* scene history at once, flagging contradictions, state violations, and unresolved threads — with confidence scores and exact source scenes |
| **Legal Clearance** | Checks for real people, brands, and copyrighted material that might need clearance before production |
| **Supervisor** | Orchestrates the pipeline (via a LangGraph state graph) and compiles everything into one report |

The Comparator's reasoning is grounded in a deterministic first pass — it identifies *which* entities recur across scenes in plain Python before ever calling an LLM, so every judgment call is traceable back to real, auditable candidates rather than an opaque "the AI decided."

## Features

- 🎭 Tracks characters and props across a full script, not just scene-to-scene
- 🚩 Three issue types: contradictions, state violations, unresolved threads — each with a confidence score
- ⚖️ Legal clearance checks for real people, brands, and copyrighted references
- 🕸️ Visual Story Timeline — see every tracked entity's state across every scene at a glance
- 🔊 Optional voice narration of the report summary
- 📊 Six demo scripts at increasing difficulty, each with a known ground-truth answer key — so detection quality can be measured, not just eyeballed
- 🧠 No hardcoded outputs — every flag comes from a live LLM call against your actual script text

## Screenshot

*(add a screenshot or short GIF of the dashboard here before sharing widely)*

## Tech stack

| Layer | Tool |
|---|---|
| Agent orchestration | LangGraph |
| LLM | Groq (`gpt-oss-120b` for reasoning, `gpt-oss-20b` for extraction) |
| Backend | FastAPI |
| Story-state storage | MongoDB |
| Frontend | React + Vite + Framer Motion |
| Voice narration | ElevenLabs *(optional)* |

## Quick start

### Backend
```bash
cd backend
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt

# create backend/.env with at minimum:
# GROQ_API_KEY=your_key

uvicorn app.main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```
Visit `http://localhost:5173`. Pick a demo script from the dropdown, or paste your own scenes separated by `---`.

### Try it without the UI
```bash
cd backend
python -m app.eval decoys_very_hard   # or weather_easy, maya_demo, chain_of_custody_hard, legal_precision
```

## Project structure

```
continuity/
├── backend/
│   ├── app/
│   │   ├── agents/        # Extractor, Comparator, Legal Clearance, Supervisor
│   │   ├── models/        # Pydantic schemas — the shared data contract every agent uses
│   │   ├── llm.py         # Groq client, retries, model routing
│   │   ├── main.py        # FastAPI routes
│   │   └── eval.py        # CLI runner against ground-truth demo sets
│   └── data/sample_scripts/
└── frontend/
    └── src/
        ├── components/    # UploadPanel, StoryTimeline, ConflictPanels, ReportSummary
        └── App.jsx
```

## Known limitations

- Plain-text scene input only — no PDF upload yet
- Voice narration (ElevenLabs) is wired up but not yet verified end-to-end with a live key
- Runs locally; not deployed to a public URL
- Entity name-matching is word-based (handles "ring" vs "gold ring"), not full semantic matching

## Why these design choices

- **Multi-agent over a single prompt**: continuity-checking genuinely splits into distinct skills — extraction, comparison, legal judgment — and separating them makes each independently promptable, testable, and debuggable.
- **One Comparator call per entity, not per scene-pair**: an earlier pairwise design burned through token budgets fast and couldn't reason across more than two scenes at once. Batching by entity fixed both.
- **The system never asserts a verdict.** Every flag comes with a confidence score and a "requires human review" status — it's built to surface evidence, not replace a script supervisor's judgment.