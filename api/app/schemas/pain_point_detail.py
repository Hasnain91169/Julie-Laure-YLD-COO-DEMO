from datetime import datetime

from pydantic import BaseModel

from app.models.enums import AutomationTypeEnum, PainCategoryEnum


class PainPointDetail(BaseModel):
    id: int
    interview_id: int
    respondent_id: int
    team: str
    role: str
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
    transcript_redacted: str | None
    summary_text: str
    score_id: int | None = None
    impact_hours_per_week: float | None = None
    effort_score: int | None = None
    confidence_score: float | None = None
    priority_score: float | None = None
    quick_win: bool = False
    automation_type: AutomationTypeEnum | None = None
    suggested_solution: str | None = None
    owner_suggestion: str | None = None
    created_at: datetime
