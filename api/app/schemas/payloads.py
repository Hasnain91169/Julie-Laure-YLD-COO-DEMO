from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class VapiRespondentInput(BaseModel):
    name: str | None = None
    email: str | None = None
    team: str
    role: str
    location: str | None = None
    consent: bool = False


class VapiIntakePayload(BaseModel):
    respondent: VapiRespondentInput
    transcript: str | None = None
    call_summary: str = ""
    extracted_fields: list[dict[str, Any]] | None = None
    started_at: datetime | None = None
    ended_at: datetime | None = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class InternalIntakePayload(BaseModel):
    respondent: VapiRespondentInput
    transcript: str | None = None
    call_summary: str = ""
    extracted_fields: list[dict[str, Any]] | None = None
    started_at: datetime | None = None
    ended_at: datetime | None = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)
