"""API FastAPI pour Exprompt."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from exprompt.models import Mode, PipelineResult
from exprompt.pipeline import Pipeline
from exprompt.provider import LLMSettings

app = FastAPI(
    title="Exprompt API",
    description="Prompt Factory — transforme un brief en prompt prêt à copier-coller",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class BriefInput(BaseModel):
    brief: str
    mode: str = "autonome"
    model: str | None = None
    api_key: str | None = None


class HealthResponse(BaseModel):
    status: str
    version: str


@app.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(status="ok", version="0.1.0")


@app.post("/pipeline", response_model=PipelineResult)
async def run_pipeline(input_data: BriefInput):
    """Exécute le pipeline Exprompt complet.

    Corps de la requête :
    ```json
    {
      "brief": "Pub TikTok pour BugCrush...",
      "mode": "autonome",
      "model": "deepseek-chat"
    }
    ```
    """
    if not input_data.brief.strip():
        raise HTTPException(status_code=400, detail="Brief vide")

    settings = LLMSettings()
    if input_data.model:
        settings.llm_model = input_data.model
    if input_data.api_key:
        settings.llm_api_key = input_data.api_key

    try:
        pipeline_mode = Mode(input_data.mode)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Mode invalide: {input_data.mode}. Choisir: strict | autonome")

    pipeline = Pipeline.from_settings(settings)
    pipeline.mode = pipeline_mode

    result = pipeline.run(input_data.brief)
    return result


@app.get("/schema")
async def get_schema():
    """Retourne le schéma de la spec YAML acceptée par Exprompt."""
    return {
        "fields": {
            "project_name": "string — Nom du projet",
            "duration_seconds": "number — Durée en secondes",
            "aspect_ratio": "string — 9:16 | 16:9 | 1:1 | 4:5",
            "orientation": "string — vertical | horizontal | carré",
            "topic": "string — Sujet principal",
            "audience": "string — Cible démographique",
            "tone": "string — Ton de la communication",
            "cta": "object — { text: string, position_s: number }",
            "constraints": "object — Règles de génération",
        }
    }
