from pydantic import BaseModel

from app.models.enums import PainCategoryEnum


class PainPointListItem(BaseModel):
    id: int
    title: str
    category: PainCategoryEnum
    team: str
    role: str
    priority_score: float | None
    impact_hours_per_week: float | None
    effort_score: int | None
    confidence_score: float | None
    quick_win: bool = False
    sensitive_flag: bool


class DashboardMetrics(BaseModel):
    total_pain_points: int
    total_hours_per_week: float
    top_categories: list[dict]
    team_heatmap: list[dict]
    top_backlog: list[dict]
    quick_wins: list[dict]
