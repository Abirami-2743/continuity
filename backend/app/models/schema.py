"""
Canonical story-state schema.

Every agent reads and writes THIS shape. Nothing in the pipeline is allowed
to invent its own ad-hoc JSON — the Extractor must produce objects that
validate against these models, and the Comparator/Legal/Supervisor agents
consume them directly. This is what turns the system from
"LLM eyeballing two scenes" into "structured facts + deterministic + LLM
reasoning over them", per the design brief.
"""
from __future__ import annotations
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class CharacterStatus(str, Enum):
    ALIVE = "alive"
    DEAD = "dead"
    UNKNOWN = "unknown"


class PropState(str, Enum):
    PRESENT = "present"
    LOST = "lost"
    DESTROYED = "destroyed"
    POSSESSED = "possessed"
    UNKNOWN = "unknown"


class Character(BaseModel):
    name: str
    status: CharacterStatus = CharacterStatus.UNKNOWN
    appearance: Optional[str] = None   # e.g. "red jacket"
    location: Optional[str] = None


class Prop(BaseModel):
    name: str
    state: PropState = PropState.UNKNOWN
    owner: Optional[str] = None


class TimelineMarker(BaseModel):
    description: str
    relative_time: Optional[str] = None  # e.g. "11:30 PM", "three years ago"


class RealWorldReference(BaseModel):
    """Anything the Legal Clearance agent needs to check: real people, brands, IP."""
    reference_text: str
    reference_type: str  # "person" | "brand" | "copyrighted_work" | "other"


class SceneFacts(BaseModel):
    """Output of the Extractor agent for a single scene. This is the atomic
    unit written into the story-state store."""
    script_id: str
    scene_id: str
    scene_index: int
    raw_text: str
    characters: list[Character] = Field(default_factory=list)
    props: list[Prop] = Field(default_factory=list)
    setting: Optional[str] = None
    weather: Optional[str] = None
    timeline_markers: list[TimelineMarker] = Field(default_factory=list)
    real_world_references: list[RealWorldReference] = Field(default_factory=list)


class ConflictType(str, Enum):
    CONTRADICTION = "contradiction"        # highest severity
    STATE_VIOLATION = "state_violation"    # high severity
    UNRESOLVED_THREAD = "unresolved_thread"  # lower severity


class Severity(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ConflictFlag(BaseModel):
    """Output of the Comparator agent — one flagged issue."""
    conflict_id: str
    conflict_type: ConflictType
    severity: Severity
    entity_name: Optional[str] = None  # which character/prop this is about — lets the UI highlight the right row, not just any scene that happens to overlap
    summary: str
    explanation: str
    source_scene_ids: list[str]
    confidence: float = Field(ge=0.0, le=1.0)
    requires_human_review: bool = True


class ClearanceFlag(BaseModel):
    """Output of the Legal Clearance agent."""
    flag_id: str
    scene_id: str
    reference_text: str
    reference_type: str
    risk_note: str
    confidence: float = Field(ge=0.0, le=1.0)
    requires_human_review: bool = True


class ContinuityReport(BaseModel):
    """Final Supervisor output — what the frontend renders."""
    script_ids: list[str]
    scenes_analyzed: int
    facts_extracted: int
    conflicts: list[ConflictFlag] = Field(default_factory=list)
    clearance_flags: list[ClearanceFlag] = Field(default_factory=list)
    scene_facts: list[SceneFacts] = Field(default_factory=list)  # real extracted data, for the timeline UI
    summary_text: str  # short natural-language summary for voice narration