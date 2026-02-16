import json
import re
from datetime import datetime, timezone
from typing import Any

import httpx
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.enums import ChannelEnum, PainCategoryEnum
from app.schemas.chatbot import COOChatRequest, COOChatResponse
from app.schemas.intake import CanonicalIntake, CanonicalPainPoint, CanonicalRespondent
from app.services.extraction import (
    extract_pain_points_deterministic,
    infer_category,
    infer_minutes,
    infer_people_affected,
    infer_systems,
)
from app.services.ingestion import IntakeIngestionService


class COOChatService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.ingestion_service = IntakeIngestionService()

    async def handle(self, session: Session, request: COOChatRequest) -> COOChatResponse:
        analysis = await self._analyze(request)

        added_to_report = False
        interview_id = None
        respondent_id = None
        pain_point_ids: list[int] = []

        if request.add_to_report and analysis["valid_concern"] and not analysis["needs_more_info"]:
            canonical = self._to_canonical_intake(request, analysis)
            interview_id, respondent_id, pain_point_ids = await self.ingestion_service.ingest(session, canonical)
            added_to_report = len(pain_point_ids) > 0

        assistant_message = self._normalize_assistant_message(str(analysis["assistant_message"]))

        return COOChatResponse(
            assistant_message=assistant_message,
            needs_more_info=bool(analysis["needs_more_info"]),
            valid_concern=bool(analysis["valid_concern"]),
            root_cause=analysis.get("root_cause"),
            rationale=str(analysis["rationale"]),
            category=str(analysis["category"]),
            estimated_impact_hours_per_week=float(analysis["estimated_impact_hours_per_week"]),
            added_to_report=added_to_report,
            interview_id=interview_id,
            respondent_id=respondent_id,
            pain_point_ids=pain_point_ids,
            created_at=datetime.now(timezone.utc),
        )

    def _normalize_assistant_message(self, text: str) -> str:
        if text.startswith("This is useful context. Could you share one more detail:"):
            return "Thanks, this helps. One quick detail would make this stronger: either frequency per week or time impact."
        return text

    def _to_canonical_intake(self, request: COOChatRequest, analysis: dict[str, Any]) -> CanonicalIntake:
        context = request.context
        user_messages = [m.content.strip() for m in request.messages if m.role.lower() == "user" and m.content.strip()]
        transcript = "\n".join(user_messages)

        category_value = str(analysis.get("category", "other"))
        if category_value not in PainCategoryEnum._value2member_map_:
            category_value = "other"

        pain_point = CanonicalPainPoint(
            title=str(analysis.get("title") or "COO complaint intake"),
            description=str(analysis.get("description") or (user_messages[-1] if user_messages else "Operational complaint")),
            category=PainCategoryEnum(category_value),
            frequency_per_week=max(0.1, float(analysis.get("frequency_per_week") or 1.0)),
            minutes_per_occurrence=max(1.0, float(analysis.get("minutes_per_occurrence") or 30.0)),
            people_affected=max(1, int(analysis.get("people_affected") or 1)),
            systems_involved=[str(x) for x in (analysis.get("systems_involved") or [])],
            current_workaround=analysis.get("current_workaround"),
            failure_modes=analysis.get("failure_modes"),
            success_definition=analysis.get("success_definition") or "Root cause removed and workflow stable",
            sensitive_flag=False,
            redaction_notes=None,
        )

        return CanonicalIntake(
            channel=ChannelEnum.webform,
            respondent=CanonicalRespondent(
                name=context.name,
                email=context.email,
                team=context.team or "COO Office",
                role=context.role or "COO",
                location=context.location,
                consent=context.consent,
            ),
            transcript=transcript if context.consent else None,
            call_summary=str(analysis.get("root_cause") or "Validated COO complaint"),
            extracted_pain_points=[pain_point],
            metadata_json={"source": "coo_chatbot", "validated": True},
        )

    async def _analyze(self, request: COOChatRequest) -> dict[str, Any]:
        if self.settings.ai_provider in {"openai", "ollama"}:
            ai_result = await self._analyze_with_llm(request)
            if ai_result is not None:
                return ai_result
        return self._analyze_deterministic(request)

    async def _analyze_with_llm(self, request: COOChatRequest) -> dict[str, Any] | None:
        system_prompt = (
            "You are a calm COO complaint intake copilot. Ask one gentle probing question at a time, identify root cause, and determine if concern is valid. "
            "Do not sound forceful or interrogative. Keep tone collaborative and concise. "
            "Respond only JSON with keys: assistant_message, needs_more_info, valid_concern, root_cause, rationale, title, "
            "description, category, frequency_per_week, minutes_per_occurrence, people_affected, systems_involved, "
            "current_workaround, failure_modes, success_definition, estimated_impact_hours_per_week."
        )
        payload = {
            "context": request.context.model_dump(),
            "messages": [m.model_dump() for m in request.messages],
            "mode": "analysis_and_probe",
        }

        try:
            if self.settings.ai_provider == "openai":
                result = await self._call_openai(system_prompt, payload)
            else:
                result = await self._call_ollama(system_prompt, payload)

            parsed = self._parse_json(result)
            if parsed is None:
                return None

            parsed.setdefault("category", "other")
            parsed.setdefault("estimated_impact_hours_per_week", 0.0)
            parsed.setdefault("systems_involved", [])
            parsed.setdefault("frequency_per_week", 1.0)
            parsed.setdefault("minutes_per_occurrence", 30.0)
            parsed.setdefault("people_affected", 1)
            parsed.setdefault("assistant_message", "Thanks for sharing this. Could you add one more detail about frequency or impact?")
            parsed.setdefault("rationale", "Insufficient signal.")
            parsed.setdefault("valid_concern", False)
            parsed.setdefault("needs_more_info", True)
            return parsed
        except Exception:
            return None

    async def _call_openai(self, system_prompt: str, payload: dict[str, Any]) -> str:
        if not self.settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY missing")

        url = f"{self.settings.openai_base_url.rstrip('/')}/chat/completions"
        body = {
            "model": self.settings.model_name,
            "temperature": 0.2,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(payload)},
            ],
        }
        headers = {"Authorization": f"Bearer {self.settings.openai_api_key}"}
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(url, json=body, headers=headers)
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]

    async def _call_ollama(self, system_prompt: str, payload: dict[str, Any]) -> str:
        url = f"{self.settings.ollama_base_url.rstrip('/')}/api/chat"
        body = {
            "model": self.settings.ollama_model,
            "stream": False,
            "format": "json",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(payload)},
            ],
        }

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(url, json=body)
            response.raise_for_status()
            return response.json().get("message", {}).get("content", "{}")

    def _parse_json(self, content: str) -> dict[str, Any] | None:
        cleaned = content.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?", "", cleaned).strip()
            cleaned = re.sub(r"```$", "", cleaned).strip()
        data = json.loads(cleaned)
        return data if isinstance(data, dict) else None

    def _analyze_deterministic(self, request: COOChatRequest) -> dict[str, Any]:
        user_messages = [m.content.strip() for m in request.messages if m.role.lower() == "user" and m.content.strip()]
        transcript = "\n".join(user_messages)
        latest = user_messages[-1] if user_messages else ""

        extracted = extract_pain_points_deterministic(transcript, latest)
        candidate = extracted[0] if extracted else None

        detail_signals = {
            "frequency": bool(re.search(r"\b\d+\s*(times?|x|per)\b|daily|weekly", transcript, flags=re.IGNORECASE)),
            "duration": bool(re.search(r"\b\d+\s*(minutes?|mins?|hours?|hrs?)\b", transcript, flags=re.IGNORECASE)),
            "people": bool(re.search(r"\b\d+\s*(people|team|staff|engineers|analysts)\b", transcript, flags=re.IGNORECASE)),
            "systems": len(infer_systems(transcript)) > 0,
            "workaround": "workaround" in transcript.lower() or "manual" in transcript.lower() or "spreadsheet" in transcript.lower(),
        }
        details_count = sum(1 for v in detail_signals.values() if v)

        category = infer_category(transcript).value if transcript else "other"
        frequency = candidate.frequency_per_week if candidate else 1.0
        minutes = candidate.minutes_per_occurrence if candidate else infer_minutes(transcript)
        people = candidate.people_affected if candidate else infer_people_affected(transcript)
        systems = candidate.systems_involved if candidate else infer_systems(transcript)
        estimated_impact = round((frequency * minutes / 60.0) * max(1, people), 2)

        concern_signal = any(
            token in transcript.lower()
            for token in [
                "manual",
                "delay",
                "approval",
                "rework",
                "bottleneck",
                "error",
                "chasing",
                "handoff",
                "spreadsheet",
                "report",
                "status",
                "reconcile",
                "mismatch",
                "missing",
                "formatting",
                "slow",
                "forever",
            ]
        )
        valid_concern = concern_signal and (estimated_impact >= 1.0 or details_count >= 3)
        needs_more_info = details_count < 2

        if not transcript:
            assistant_message = (
                "Thanks for raising this. What is the main issue you are seeing in operations?"
            )
        elif needs_more_info:
            assistant_message = (
                "Thanks, this helps. One quick detail would make this stronger: either frequency per week or time impact."
            )
        elif valid_concern:
            assistant_message = (
                "Understood. This looks like a valid operational concern with measurable impact. "
                "I can add it to the report backlog whenever you are ready."
            )
        else:
            assistant_message = (
                "I have captured the issue. With a little more impact data, I can reassess whether it should be prioritized in the backlog."
            )

        root_cause = (
            candidate.failure_modes if candidate and candidate.failure_modes else "Manual handoffs and fragmented systems create avoidable delays and rework"
        )
        rationale = (
            f"Signals: details={details_count}/5, impact={estimated_impact}h/week, systems={len(systems)}. "
            f"Concern classified as {'valid' if valid_concern else 'not yet valid'}"
        )

        return {
            "assistant_message": assistant_message,
            "needs_more_info": needs_more_info,
            "valid_concern": valid_concern,
            "root_cause": root_cause,
            "rationale": rationale,
            "title": candidate.title if candidate else "COO complaint intake",
            "description": candidate.description if candidate else (latest or "Operational complaint"),
            "category": category,
            "frequency_per_week": frequency,
            "minutes_per_occurrence": minutes,
            "people_affected": people,
            "systems_involved": systems,
            "current_workaround": candidate.current_workaround if candidate else "Manual follow-up and spreadsheet tracking",
            "failure_modes": candidate.failure_modes if candidate else "Delays, missed updates, inconsistent execution",
            "success_definition": candidate.success_definition if candidate else "A reliable, automated workflow with clear ownership",
            "estimated_impact_hours_per_week": estimated_impact,
        }
