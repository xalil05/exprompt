"""Modèles Pydantic pour le pipeline Exprompt."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ─── Enums ───

class Mode(str, Enum):
    strict = "strict"
    autonome = "autonome"


class AspectRatio(str, Enum):
    vertical = "9:16"
    horizontal = "16:9"
    carre = "1:1"
    paysage = "4:5"


class Orientation(str, Enum):
    vertical = "vertical"
    horizontal = "horizontal"
    carre = "carre"


class QAStatus(str, Enum):
    pass_ = "PASS"
    fail = "FAIL"
    pass_with_warnings = "PASS_WITH_WARNINGS"


# ─── Modèles de la spec ───

class TimelineSegment(BaseModel):
    segment_id: int
    start_s: float
    end_s: float
    description: str
    shot_type: str = "medium"


class TextOverlay(BaseModel):
    id: str
    text: str
    start_s: float
    end_s: float
    style: str | None = None


class CTA(BaseModel):
    text: str
    position_s: float


class VisualStyle(BaseModel):
    mood: str = ""
    lighting: str = ""
    color_palette: str | list[str] = ""
    reference_style: str = ""


class Constraints(BaseModel):
    no_shocking: bool = True
    no_health_claims: bool = True
    no_false_certifications: bool = True
    must_include_brand: bool = True
    brand_name: str = ""
    no_bullshit: bool = False
    no_voice_over: bool = False


class Spec(BaseModel):
    """Specification structurée produite par l'agent INTAKE."""

    project_name: str
    language: str = "fr"
    duration_seconds: int = 10
    aspect_ratio: str = "9:16"
    orientation: str = "vertical"
    topic: str = ""
    audience: str = ""
    tone: str = ""
    timeline: list[TimelineSegment] = []
    text_overlays: list[TextOverlay] = []
    no_voice_over: bool = False
    cta: CTA | None = None
    visual_style: VisualStyle = Field(default_factory=VisualStyle)
    constraints: Constraints = Field(default_factory=Constraints)
    missing_fields: list[str] = []
    assumptions: list[str] = []
    user_notes: str = ""


# ─── Résultats du pipeline ───

class IntakeResult(BaseModel):
    spec: Spec
    completeness: float  # 0-100
    confidence: float  # 0-100
    questions: list[str] = []
    assumptions: list[str] = []
    status: str = "complete"  # complete | needs_input


class QACheck(BaseModel):
    check: str
    result: str  # PASS | FAIL | WARN
    detail: str


class QAReport(BaseModel):
    status: QAStatus
    checks: list[QACheck] = []
    critical_failures: bool = False
    warnings_count: int = 0
    summary: str = ""


class DeliverySpec(BaseModel):
    output_format: str = "Prompt texte prêt à copier-coller"
    required_fields: list[str] = []


class Variant(BaseModel):
    name: str
    description: str
    prompt: str
    transformeter_level: int = 5


class PipelineResult(BaseModel):
    """Résultat complet du pipeline Exprompt."""

    brief: str
    mode: str
    spec: Spec
    intake: IntakeResult
    deliverable_prompt: str
    delivery_spec: DeliverySpec
    auto_qa_report: QAReport
    variants: list[Variant] = []
    generated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    version: str = "0.1.0"
