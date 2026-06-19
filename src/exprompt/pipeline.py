"""Pipeline Exprompt — INTAKE → CREATIVE_WRITER → AUTO_QA."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

import yaml

from exprompt.agents import load_prompt
from exprompt.models import (
    CTA,
    Constraints,
    DeliverySpec,
    IntakeResult,
    Mode,
    PipelineResult,
    QACheck,
    QAReport,
    QAStatus,
    Spec,
    TimelineSegment,
    Variant,
    VisualStyle,
)
from exprompt.provider import BaseProvider, LLMSettings, get_provider


@dataclass
class Pipeline:
    """Orchestrateur du pipeline Exprompt."""

    provider: BaseProvider
    mode: Mode = Mode.autonome

    @classmethod
    def from_settings(cls, settings: LLMSettings | None = None) -> Pipeline:
        return cls(provider=get_provider(settings))

    def run(self, brief: str) -> PipelineResult:
        """Exécute le pipeline complet : INTAKE → CREATIVE_WRITER → AUTO_QA."""
        intake_result = self._intake(brief)
        spec = intake_result.spec

        writer_result = self._creative_writer(spec)
        deliverable_prompt = writer_result["deliverable_prompt"]
        delivery_spec_dict = writer_result.get("delivery_spec", {}) or {}
        req_fields = delivery_spec_dict.get("required_fields", []) or []
        # Flatten — le LLM retourne parfois des dicts au lieu de strings
        flat_fields = []
        for f in req_fields:
            if isinstance(f, dict):
                for v in f.values():
                    flat_fields.append(str(v))
            else:
                flat_fields.append(str(f))

        qa_report = self._auto_qa(spec, deliverable_prompt)

        variants_data = writer_result.get("variants", []) or []
        variants = [
            Variant(name=v.get("name", ""), description=v.get("description", ""),
                    prompt=v.get("prompt", ""), transformeter_level=v.get("transformeter_level", 5))
            for v in variants_data
        ]
 
        return PipelineResult(
            brief=brief,
            mode=self.mode.value,
            spec=spec,
            intake=intake_result,
            deliverable_prompt=deliverable_prompt,
            delivery_spec=DeliverySpec(
                output_format=delivery_spec_dict.get("output_format", "Prompt texte"),
                required_fields=flat_fields,
            ),
            auto_qa_report=qa_report,
            variants=variants,
        )

    def _intake(self, brief: str) -> IntakeResult:
        """Étape A : INTAKE — analyse le brief → spec structurée."""
        system_prompt = load_prompt("intake", mode=self.mode.value)

        raw = self.provider.chat(system=system_prompt, user=brief, temperature=0.3)

        # Extraction du YAML depuis la réponse
        yaml_str = self._extract_yaml(raw.content)
        data = yaml.safe_load(yaml_str)

        spec_data = data.get("spec", data)
        analysis = data.get("intake_analysis", {})

        spec = self._dict_to_spec(spec_data)

        return IntakeResult(
            spec=spec,
            completeness=analysis.get("completeness", 70),
            confidence=analysis.get("confidence", 70),
            questions=analysis.get("questions", []),
            assumptions=analysis.get("assumptions", []),
            status=data.get("status", "complete"),
        )

    def _creative_writer(self, spec: Spec) -> dict:
        """Étape B : CREATIVE_WRITER — spec → deliverable_prompt."""
        system_prompt = load_prompt("creative_writer")
        user_prompt = yaml.dump(spec.model_dump(), allow_unicode=True, default_flow_style=False)

        raw = self.provider.chat(system=system_prompt, user=user_prompt, temperature=0.4)

        return self._parse_yaml_block(raw.content) or {
            "deliverable_prompt": raw.content,
            "delivery_spec": {"output_format": "texte", "required_fields": []},
        }

    def _auto_qa(self, spec: Spec, prompt: str) -> QAReport:
        """Étape C : AUTO_QA — validation qualité."""
        system_prompt = load_prompt("auto_qa")
        user_prompt = (
            f"--- SPEC ---\n{yaml.dump(spec.model_dump(), allow_unicode=True)}\n"
            f"--- DELIVERABLE PROMPT ---\n{prompt}"
        )

        raw = self.provider.chat(system=system_prompt, user=user_prompt, temperature=0.2)

        data = self._parse_yaml_block(raw.content) or {}
        report = data.get("auto_qa_report", {})

        checks = [
            QACheck(check=c.get("check", ""), result=c.get("result", "WARN"), detail=c.get("detail", ""))
            for c in report.get("checks", [])
        ]

        status_str = report.get("status", "PASS")
        try:
            status = QAStatus(status_str)
        except ValueError:
            status = QAStatus.pass_

        return QAReport(
            status=status,
            checks=checks,
            critical_failures=report.get("critical_failures", False),
            warnings_count=report.get("warnings_count", 0),
            summary=report.get("summary", "AUTO_QA terminé"),
        )

    # ─── Helpers ───

    def _dict_to_spec(self, data: dict) -> Spec:
        """Convertit un dict brut en objet Spec validé, avec des defaults robustes."""
        timeline = []
        for seg in data.get("timeline", []) or []:
            if not isinstance(seg, dict):
                continue
            timeline.append(TimelineSegment(
                segment_id=int(seg.get("segment_id", 0)),
                start_s=float(seg.get("start_s", 0)),
                end_s=float(seg.get("end_s", 0)),
                description=str(seg.get("description", "")),
                shot_type=str(seg.get("shot_type", "medium")),
            ))

        cta_data = data.get("cta")
        cta = None
        if cta_data and isinstance(cta_data, dict) and cta_data.get("text"):
            cta = CTA(
                text=str(cta_data["text"]),
                position_s=float(cta_data.get("position_s", 0)),
            )

        constraints_data = data.get("constraints", {}) or {}
        constraints = Constraints(
            no_shocking=bool(constraints_data.get("no_shocking", True)),
            no_health_claims=bool(constraints_data.get("no_health_claims", True)),
            no_false_certifications=bool(constraints_data.get("no_false_certifications", True)),
            must_include_brand=bool(constraints_data.get("must_include_brand", True)),
            brand_name=str(constraints_data.get("brand_name", "")),
            no_bullshit=bool(constraints_data.get("no_bullshit", False)),
            no_voice_over=bool(constraints_data.get("no_voice_over", False)),
        )

        visual_data = data.get("visual_style", {}) or {}
        cp = visual_data.get("color_palette", "")
        if isinstance(cp, list):
            cp = ", ".join(str(c) for c in cp)
        elif isinstance(cp, dict):
            cp = ", ".join(f"{k}:{v}" for k, v in cp.items())
        visual_style = VisualStyle(
            mood=str(visual_data.get("mood", "")),
            lighting=str(visual_data.get("lighting", "")),
            color_palette=cp,
            reference_style=str(visual_data.get("reference_style", "")),
        )

        return Spec(
            project_name=str(data.get("project_name", "")),
            language=str(data.get("language", "fr")),
            duration_seconds=int(data.get("duration_seconds", 10) or 10),
            aspect_ratio=str(data.get("aspect_ratio", "9:16") or "9:16"),
            orientation=str(data.get("orientation", "vertical") or "vertical"),
            topic=str(data.get("topic", "")),
            audience=str(data.get("audience", "")),
            tone=str(data.get("tone", "")),
            timeline=timeline,
            no_voice_over=bool(data.get("no_voice_over", False)),
            cta=cta,
            visual_style=visual_style,
            constraints=constraints,
            missing_fields=[str(f) for f in (data.get("missing_fields", []) or [])],
            assumptions=[str(a) for a in (data.get("assumptions", []) or [])],
            user_notes=str(data.get("user_notes", "")),
        )

    def _extract_yaml(self, text: str) -> str:
        """Extrait un bloc YAML ```yaml ... ``` d'un texte."""
        # Cherche ```yaml ... ``` ou ``` ... ```
        match = re.search(r"```(?:yaml)?\s*\n(.*?)\n```", text, re.DOTALL)
        if match:
            return match.group(1).strip()
        # Sinon, prend tout le texte
        return text.strip()

    def _parse_yaml_block(self, text: str) -> dict | None:
        """Parse un bloc YAML dans un texte, retourne dict ou None."""
        try:
            yaml_str = self._extract_yaml(text)
            return yaml.safe_load(yaml_str)
        except (yaml.YAMLError, json.JSONDecodeError):
            return None
