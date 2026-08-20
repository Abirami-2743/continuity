from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel

from app.agents.supervisor import run_pipeline
from app.storage import save_report, get_report, list_reports
from app.voice import narrate

app = FastAPI(title="Continuity API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class AnalyzeRequest(BaseModel):
    script_id: str
    scenes: list[str]   # raw scene text, one entry per scene


@app.post("/api/analyze")
def analyze(req: AnalyzeRequest):
    if not req.scenes:
        raise HTTPException(400, "No scenes provided.")
    report = run_pipeline(req.script_id, req.scenes)
    save_report(req.script_id, report.model_dump())
    return report.model_dump()


@app.get("/api/reports")
def reports():
    return list_reports()


@app.get("/api/reports/{script_id}")
def report(script_id: str):
    result = get_report(script_id)
    if not result:
        raise HTTPException(404, "Report not found.")
    return result


@app.get("/api/reports/{script_id}/narrate")
def narrate_report(script_id: str):
    result = get_report(script_id)
    if not result:
        raise HTTPException(404, "Report not found.")
    audio = narrate(result["summary_text"])
    return Response(content=audio, media_type="audio/mpeg")


@app.get("/api/health")
def health():
    return {"status": "ok"}
