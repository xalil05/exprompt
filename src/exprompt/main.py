"""CLI Exprompt — Point d'entrée en ligne de commande."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import typer
import yaml
from rich.console import Console
from rich.table import Table

from exprompt.models import Mode
from exprompt.pipeline import Pipeline
from exprompt.provider import LLMSettings

app = typer.Typer(
    name="exprompt",
    help="Prompt Factory — transforme un brief en prompt prêt à copier-coller",
    no_args_is_help=True,
)
console = Console()


@app.command()
def run(
    brief: str = typer.Argument(None, help="Texte du brief (ou utilise --file)"),
    file: Path = typer.Option(None, "--file", "-f", help="Fichier contenant le brief"),
    mode: Mode = typer.Option(Mode.autonome, "--mode", "-m", help="Mode pipeline"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Sortie JSON"),
    model: str = typer.Option(None, "--model", help="Override modèle LLM"),
    api_key: str = typer.Option(None, "--api-key", help="Override clé API"),
):
    """Exécute le pipeline Exprompt sur un brief.

    Exemples :
      echo "Pub TikTok pour BugCrush..." | exprompt
      exprompt --file brief.txt
      exprompt --brief "Pub Instagram pour..."
    """
    # Chargement du brief
    if file:
        brief_text = file.read_text(encoding="utf-8")
    elif brief:
        brief_text = brief
    elif not sys.stdin.isatty():
        brief_text = sys.stdin.read().strip()
    else:
        console.print("[red]❌ Fournis un brief : exprompt \"ton brief\" ou --file brief.txt[/red]")
        raise typer.Exit(1)

    if not brief_text.strip():
        console.print("[red]❌ Brief vide[/red]")
        raise typer.Exit(1)

    # Pipeline
    settings = LLMSettings()
    if model:
        settings.llm_model = model
    if api_key:
        settings.llm_api_key = api_key

    pipeline = Pipeline.from_settings(settings)
    pipeline.mode = mode

    console.print(f"[bold blue]🧪 Exprompt v0.1.0 — Mode {mode.value}[/bold blue]")
    console.print(f"🔗 Provider: {settings.llm_provider} | Modèle: {settings.llm_model}")
    console.print()

    with console.status("[bold green]🔍 INTAKE en cours...[/bold green]"):
        result = pipeline.run(brief_text)

    # Affichage
    if json_output:
        import json
        data = result.model_dump(mode="json")
        console.print_json(data=data)
        return

    # ── Spec ──
    console.print("[bold cyan]📋 SPEC INTAKE[/bold cyan]")
    console.print(f"  Projet: {result.spec.project_name}")
    console.print(f"  Durée: {result.spec.duration_seconds}s | Ratio: {result.spec.aspect_ratio}")
    console.print(f"  Audience: {result.spec.audience}")
    console.print(f"  Ton: {result.spec.tone}")
    if result.spec.cta:
        console.print(f"  CTA: \"{result.spec.cta.text}\" (à {result.spec.cta.position_s}s)")
    if result.intake.assumptions:
        console.print(f"  Assumptions: {len(result.intake.assumptions)}")
    console.print(f"  Complétude: [bold]{result.intake.completeness:.0f}%[/bold] | Confiance: {result.intake.confidence:.0f}%")
    console.print()

    # ── Timeline ──
    if result.spec.timeline:
        table = Table(title="Timeline")
        table.add_column("Seg", style="dim")
        table.add_column("Début", justify="right")
        table.add_column("Fin", justify="right")
        table.add_column("Description")
        for seg in result.spec.timeline:
            table.add_row(str(seg.segment_id), f"{seg.start_s:.0f}s", f"{seg.end_s:.0f}s", seg.description)
        console.print(table)
        console.print()

    # ── Deliverable Prompt ──
    console.print("[bold cyan]🎯 DELIVERABLE PROMPT[/bold cyan]")
    console.print(result.deliverable_prompt)
    console.print()

    # ── AUTO_QA ──
    status_color = {
        "PASS": "green",
        "PASS_WITH_WARNINGS": "yellow",
        "FAIL": "red",
    }.get(result.auto_qa_report.status.value, "white")
    console.print(f"[bold {status_color}]🔍 AUTO_QA: {result.auto_qa_report.status.value}[/bold {status_color}]")
    for check in result.auto_qa_report.checks:
        icon = "✅" if check.result == "PASS" else ("⚠️" if check.result == "WARN" else "❌")
        console.print(f"  {icon} {check.check}: {check.detail}")
    console.print(f"  → {result.auto_qa_report.summary}")
    console.print()

    # ── Variants ──
    if result.variants:
        console.print("[bold cyan]🔄 VARIANTS[/bold cyan]")
        for v in result.variants:
            console.print(f"  • {v.name}: {v.description}")

    console.print()
    console.print("[bold green]✅ Pipeline terminé ![/bold green]")


@app.command()
def serve(
    host: str = "0.0.0.0",
    port: int = 8022,
    workers: int = 1,
):
    """Lance le serveur API FastAPI."""
    import uvicorn

    uvicorn.run(
        "exprompt.api:app",
        host=host,
        port=port,
        workers=workers,
        log_level="info",
    )


if __name__ == "__main__":
    app()
