from collections import Counter, defaultdict
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.interview import Interview
from app.models.pain_point import PainPoint
from app.models.respondent import Respondent
from app.models.score import Score


def load_pain_points_with_context(session: Session) -> list[PainPoint]:
    stmt = select(PainPoint).options(
        joinedload(PainPoint.score),
        joinedload(PainPoint.interview).joinedload(Interview.respondent),
    )
    return session.scalars(stmt).all()


def dashboard_metrics(session: Session) -> dict[str, Any]:
    pain_points = load_pain_points_with_context(session)
    total_hours = round(sum((pp.score.impact_hours_per_week if pp.score else 0.0) for pp in pain_points), 2)

    category_counter = Counter(pp.category.value for pp in pain_points)
    top_categories = [{"category": category, "count": count} for category, count in category_counter.most_common(8)]

    heatmap: dict[str, Counter[str]] = defaultdict(Counter)
    for pp in pain_points:
        team = pp.interview.respondent.team if pp.interview and pp.interview.respondent else "Unknown"
        heatmap[team][pp.category.value] += 1

    team_heatmap = [
        {"team": team, "categories": dict(counter), "total": sum(counter.values())}
        for team, counter in sorted(heatmap.items(), key=lambda item: sum(item[1].values()), reverse=True)
    ]

    backlog = sorted(
        [pp for pp in pain_points if pp.score],
        key=lambda pp: pp.score.priority_score,
        reverse=True,
    )[:10]
    top_backlog = [
        {
            "pain_point_id": pp.id,
            "title": pp.title,
            "team": pp.interview.respondent.team if pp.interview and pp.interview.respondent else "Unknown",
            "category": pp.category.value,
            "impact_hours_per_week": pp.score.impact_hours_per_week,
            "effort_score": pp.score.effort_score,
            "confidence_score": pp.score.confidence_score,
            "priority_score": pp.score.priority_score,
            "automation_type": pp.score.automation_type.value,
            "suggested_solution": pp.score.suggested_solution,
            "owner_suggestion": pp.score.owner_suggestion,
        }
        for pp in backlog
    ]

    quick_wins = [
        {
            "pain_point_id": pp.id,
            "title": pp.title,
            "team": pp.interview.respondent.team if pp.interview and pp.interview.respondent else "Unknown",
            "impact_hours_per_week": pp.score.impact_hours_per_week,
            "priority_score": pp.score.priority_score,
        }
        for pp in backlog
        if pp.score.quick_win
    ]

    return {
        "total_pain_points": len(pain_points),
        "total_hours_per_week": total_hours,
        "top_categories": top_categories,
        "team_heatmap": team_heatmap,
        "top_backlog": top_backlog,
        "quick_wins": quick_wins,
    }


def report_context(session: Session) -> dict[str, Any]:
    metrics = dashboard_metrics(session)
    pain_points = load_pain_points_with_context(session)

    systems_counter: Counter[str] = Counter()
    for pp in pain_points:
        for system in pp.systems_involved or []:
            systems_counter[system] += 1

    non_sensitive_quotes = []
    for pp in pain_points:
        if pp.sensitive_flag:
            continue
        interview = pp.interview
        if not interview or not interview.transcript_redacted:
            continue
        snippet = interview.transcript_redacted[:220].strip()
        if snippet:
            non_sensitive_quotes.append(
                {
                    "pain_point_id": pp.id,
                    "team": interview.respondent.team if interview.respondent else "Unknown",
                    "quote": snippet,
                }
            )

    return {
        "generated": __import__("datetime").datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
        "executive_quick_wins": metrics["quick_wins"][:3],
        "estimated_hours_saved": round(sum(item["impact_hours_per_week"] for item in metrics["quick_wins"][:3]), 2),
        "top_backlog": metrics["top_backlog"],
        "team_breakdown": metrics["team_heatmap"],
        "category_breakdown": metrics["top_categories"],
        "systems_map": [{"system": name, "mentions": count} for name, count in systems_counter.most_common(12)],
        "quotes": non_sensitive_quotes[:15],
        "kpis": metrics,
    }
