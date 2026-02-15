from datetime import datetime

from pydantic import BaseModel

from app.models.enums import AutomationTypeEnum


class ScoreRead(BaseModel):
    id: int
    pain_point_id: int
    impact_hours_per_week: float
    effort_score: int
    confidence_score: float
    priority_score: float
    rationale: str
    automation_type: AutomationTypeEnum
    suggested_solution: str
    dependencies: str | None
    owner_suggestion: str | None
    quick_win: bool
    updated_at: datetime

    model_config = {"from_attributes": True}


class ScoreRecomputeRequest(BaseModel):
    pain_point_id: int | None = None
