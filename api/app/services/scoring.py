from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.enums import AutomationTypeEnum, PainCategoryEnum
from app.models.pain_point import PainPoint
from app.models.score import Score


def calculate_impact_hours_per_week(pain_point: PainPoint) -> float:
    return round(
        (pain_point.frequency_per_week * pain_point.minutes_per_occurrence / 60.0)
        * max(1, pain_point.people_affected),
        2,
    )


def infer_effort_score(pain_point: PainPoint) -> int:
    text = " ".join(
        filter(
            None,
            [
                pain_point.title,
                pain_point.description,
                pain_point.current_workaround,
                pain_point.failure_modes,
            ],
        )
    ).lower()
    systems_count = len(pain_point.systems_involved or [])

    high_risk_terms = ("compliance", "regulated", "security", "pii", "audit")
    if systems_count >= 4 or any(term in text for term in high_risk_terms):
        return 5

    medium_terms = ("auth", "authentication", "api", "sso", "integration", "mapping")
    if systems_count >= 2 or any(term in text for term in medium_terms):
        return 3

    low_terms = ("zapier", "sheet", "excel", "forms", "manual")
    if any(term in text for term in low_terms):
        return 2

    return 2


def infer_automation_type(pain_point: PainPoint, effort_score: int) -> AutomationTypeEnum:
    description = f"{pain_point.title} {pain_point.description}".lower()
    if "approval" in description or "workflow" in description:
        return AutomationTypeEnum.low_code if effort_score <= 2 else AutomationTypeEnum.api_integration
    if "report" in description or pain_point.category == PainCategoryEnum.reporting:
        return AutomationTypeEnum.internal_tool
    if "email" in description or "summary" in description or "draft" in description:
        return AutomationTypeEnum.ai_assist
    if effort_score >= 5:
        return AutomationTypeEnum.process_change
    return AutomationTypeEnum.api_integration


def infer_confidence_score(session: Session, pain_point: PainPoint) -> float:
    fields = [
        bool(pain_point.title),
        bool(pain_point.description),
        pain_point.frequency_per_week > 0,
        pain_point.minutes_per_occurrence > 0,
        pain_point.people_affected > 0,
        bool(pain_point.systems_involved),
        bool(pain_point.success_definition),
    ]
    completeness = sum(fields) / len(fields)

    repeats_stmt = select(func.count(PainPoint.id)).where(func.lower(PainPoint.title) == pain_point.title.lower())
    repeated_mentions = session.scalar(repeats_stmt) or 1
    repeat_factor = min(1.0, repeated_mentions / 3)

    clarity_factor = 1.0 if len((pain_point.description or "").split()) >= 10 else 0.6

    confidence = 0.25 + 0.45 * completeness + 0.2 * repeat_factor + 0.1 * clarity_factor
    return round(min(1.0, max(0.1, confidence)), 2)


def suggest_solution(pain_point: PainPoint, automation_type: AutomationTypeEnum) -> str:
    systems = ", ".join(pain_point.systems_involved) if pain_point.systems_involved else "existing systems"
    if automation_type == AutomationTypeEnum.low_code:
        return f"Build a low-code workflow for approvals and notifications across {systems}."
    if automation_type == AutomationTypeEnum.api_integration:
        return f"Implement API integration and data mapping between {systems}."
    if automation_type == AutomationTypeEnum.ai_assist:
        return "Deploy AI-assisted triage/summarisation to reduce manual handling effort."
    if automation_type == AutomationTypeEnum.internal_tool:
        return "Build an internal operations dashboard with automated data pulls and alerts."
    return "Redesign process ownership and controls before automating high-risk steps."


def suggest_owner(pain_point: PainPoint) -> str:
    mapping = {
        PainCategoryEnum.finance_ops: "Finance Operations Lead",
        PainCategoryEnum.sales_ops: "Sales Operations Lead",
        PainCategoryEnum.client_ops: "Client Services Lead",
        PainCategoryEnum.onboarding: "People Operations Lead",
        PainCategoryEnum.access_mgmt: "IT / Security Lead",
        PainCategoryEnum.reporting: "Data & Insights Lead",
    }
    return mapping.get(pain_point.category, "COO / Operations Excellence")


def upsert_score(session: Session, pain_point: PainPoint) -> Score:
    settings = get_settings()
    impact = calculate_impact_hours_per_week(pain_point)
    effort = infer_effort_score(pain_point)
    confidence = infer_confidence_score(session, pain_point)
    priority = round((impact * confidence) / effort, 4)
    automation_type = infer_automation_type(pain_point, effort)
    quick_win = effort <= 2 and impact >= settings.report_quickwin_impact_threshold_hours

    rationale = (
        f"Impact={impact}h/week from frequency({pain_point.frequency_per_week}) x duration({pain_point.minutes_per_occurrence}m)"
        f" x people({max(1, pain_point.people_affected)}). Confidence={confidence} from completeness/repeat signals;"
        f" effort={effort} based on systems complexity ({len(pain_point.systems_involved)} systems)."
    )

    score = session.scalar(select(Score).where(Score.pain_point_id == pain_point.id))
    if score is None:
        score = Score(pain_point_id=pain_point.id)
        session.add(score)

    score.impact_hours_per_week = impact
    score.effort_score = effort
    score.confidence_score = confidence
    score.priority_score = priority
    score.rationale = rationale
    score.automation_type = automation_type
    score.suggested_solution = suggest_solution(pain_point, automation_type)
    score.dependencies = ", ".join(pain_point.systems_involved) if pain_point.systems_involved else None
    score.owner_suggestion = suggest_owner(pain_point)
    score.quick_win = quick_win
    score.updated_at = datetime.now(timezone.utc)
    return score


def recompute_scores(session: Session, pain_point_id: int | None = None) -> list[Score]:
    stmt = select(PainPoint)
    if pain_point_id is not None:
        stmt = stmt.where(PainPoint.id == pain_point_id)

    pain_points = session.scalars(stmt).all()
    results = [upsert_score(session, pain_point) for pain_point in pain_points]
    session.commit()
    for score in results:
        session.refresh(score)
    return results
