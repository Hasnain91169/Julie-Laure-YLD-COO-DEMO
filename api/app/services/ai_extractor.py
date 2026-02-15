import json
import re
from typing import Any

import httpx

from app.config import get_settings
from app.schemas.intake import CanonicalPainPoint


EXTRACTION_PROMPT = """
Extract operational pain points from this interview transcript and summary.
Return ONLY JSON as an array. Each item must include:
title, description, category, frequency_per_week, minutes_per_occurrence, people_affected,
systems_involved (array), current_workaround, failure_modes, success_definition, sensitive_flag.
Use categories from: onboarding, approvals, reporting, comms, finance_ops, sales_ops, client_ops, access_mgmt, other.
""".strip()


def _parse_json_block(content: str) -> list[dict[str, Any]]:
    cleaned = content.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?", "", cleaned).strip()
        cleaned = re.sub(r"```$", "", cleaned).strip()

    data = json.loads(cleaned)
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict) and isinstance(data.get("pain_points"), list):
        return [item for item in data["pain_points"] if isinstance(item, dict)]
    return []


class AIExtractor:
    def __init__(self) -> None:
        self.settings = get_settings()

    async def extract(self, transcript: str | None, summary: str | None) -> list[CanonicalPainPoint] | None:
        if self.settings.ai_provider == "none":
            return None

        body = {
            "transcript": transcript or "",
            "summary": summary or "",
        }

        try:
            if self.settings.ai_provider == "openai":
                raw = await self._extract_openai(body)
            else:
                raw = await self._extract_ollama(body)

            return [CanonicalPainPoint.model_validate(item) for item in raw]
        except Exception:
            return None

    async def _extract_openai(self, body: dict[str, str]) -> list[dict[str, Any]]:
        if not self.settings.openai_api_key:
            return []

        url = f"{self.settings.openai_base_url.rstrip('/')}/chat/completions"
        payload = {
            "model": self.settings.model_name,
            "temperature": 0,
            "messages": [
                {"role": "system", "content": EXTRACTION_PROMPT},
                {"role": "user", "content": json.dumps(body)},
            ],
        }
        headers = {"Authorization": f"Bearer {self.settings.openai_api_key}"}

        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            return _parse_json_block(content)

    async def _extract_ollama(self, body: dict[str, str]) -> list[dict[str, Any]]:
        url = f"{self.settings.ollama_base_url.rstrip('/')}/api/chat"
        payload = {
            "model": self.settings.ollama_model,
            "stream": False,
            "format": "json",
            "messages": [
                {"role": "system", "content": EXTRACTION_PROMPT},
                {"role": "user", "content": json.dumps(body)},
            ],
        }

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            content = response.json().get("message", {}).get("content", "[]")
            return _parse_json_block(content)
