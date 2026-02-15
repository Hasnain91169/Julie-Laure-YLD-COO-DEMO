from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import PainCategoryEnum


class PainPointCreate(BaseModel):
    interview_id: int
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


class PainPointUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    category: PainCategoryEnum | None = None
    frequency_per_week: float | None = None
    minutes_per_occurrence: float | None = None
    people_affected: int | None = None
    systems_involved: list[str] | None = None
    current_workaround: str | None = None
    failure_modes: str | None = None
    success_definition: str | None = None
    sensitive_flag: bool | None = None
    redaction_notes: str | None = None


class PainPointRead(BaseModel):
    id: int
    interview_id: int
    title: str
    description: str
    category: PainCategoryEnum
    frequency_per_week: float
    minutes_per_occurrence: float
    people_affected: int
    systems_involved: list[str]
    current_workaround: str | None
    failure_modes: str | None
    success_definition: str | None
    sensitive_flag: bool
    redaction_notes: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
