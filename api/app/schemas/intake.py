from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.models.enums import ChannelEnum, PainCategoryEnum


class CanonicalRespondent(BaseModel):
    name: str | None = None
    email: str | None = None
    team: str
    role: str
    location: str | None = None
    consent: bool = False


class CanonicalPainPoint(BaseModel):
    title: str
    description: str
    category: PainCategoryEnum = PainCategoryEnum.other
    frequency_per_week: float = 1.0
    minutes_per_occurrence: float = 30.0
    people_affected: int = 1
    systems_involved: list[str] = Field(default_factory=list)
    current_workaround: str | None = None
    failure_modes: str | None = None
    success_definition: str | None = None
    sensitive_flag: bool = False
    redaction_notes: str | None = None


class CanonicalIntake(BaseModel):
    channel: ChannelEnum
    respondent: CanonicalRespondent
    started_at: datetime | None = None
    ended_at: datetime | None = None
    transcript: str | None = None
    call_summary: str = ""
    extracted_pain_points: list[CanonicalPainPoint] = Field(default_factory=list)
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class IntakeResponse(BaseModel):
    interview_id: int
    respondent_id: int
    pain_point_ids: list[int]
