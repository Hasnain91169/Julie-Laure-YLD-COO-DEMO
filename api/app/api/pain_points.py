from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, select
from sqlalchemy.orm import Session, joinedload

from app.api.deps import require_app_password
from app.db import get_session
from app.models.interview import Interview
from app.models.pain_point import PainPoint
from app.models.respondent import Respondent
from app.models.score import Score
from app.schemas.pain_point import PainPointCreate, PainPointRead, PainPointUpdate
from app.schemas.pain_point_detail import PainPointDetail
from app.schemas.views import PainPointListItem
from app.services.scoring import upsert_score

router = APIRouter(prefix="/pain-points", tags=["pain-points"], dependencies=[Depends(require_app_password)])


@router.get("", response_model=list[PainPointListItem])
def list_pain_points(
    team: str | None = Query(default=None),
    category: str | None = Query(default=None),
    priority_min: float | None = Query(default=None),
    session: Session = Depends(get_session),
) -> list[PainPointListItem]:
    stmt = (
        select(PainPoint)
        .options(
            joinedload(PainPoint.interview).joinedload(Interview.respondent),
            joinedload(PainPoint.score),
        )
        .order_by(desc(PainPoint.created_at))
    )

    items = session.scalars(stmt).all()
    results: list[PainPointListItem] = []
    for item in items:
        respondent = item.interview.respondent if item.interview else None
        score = item.score

        if team and (not respondent or respondent.team != team):
            continue
        if category and item.category.value != category:
            continue
        if priority_min is not None and (not score or score.priority_score < priority_min):
            continue

        results.append(
            PainPointListItem(
                id=item.id,
                title=item.title,
                category=item.category,
                team=respondent.team if respondent else "Unknown",
                role=respondent.role if respondent else "Unknown",
                priority_score=score.priority_score if score else None,
                impact_hours_per_week=score.impact_hours_per_week if score else None,
                effort_score=score.effort_score if score else None,
                confidence_score=score.confidence_score if score else None,
                quick_win=score.quick_win if score else False,
                sensitive_flag=item.sensitive_flag,
            )
        )

    return sorted(results, key=lambda row: row.priority_score or 0, reverse=True)


@router.get("/{pain_point_id}", response_model=PainPointDetail)
def get_pain_point(pain_point_id: int, session: Session = Depends(get_session)) -> PainPointDetail:
    stmt = (
        select(PainPoint)
        .where(PainPoint.id == pain_point_id)
        .options(
            joinedload(PainPoint.interview).joinedload(Interview.respondent),
            joinedload(PainPoint.score),
        )
    )
    item = session.scalar(stmt)
    if item is None:
        raise HTTPException(status_code=404, detail="Pain point not found")

    interview = item.interview
    respondent = interview.respondent if interview else None
    score = item.score

    return PainPointDetail(
        id=item.id,
        interview_id=item.interview_id,
        respondent_id=respondent.id if respondent else 0,
        team=respondent.team if respondent else "Unknown",
        role=respondent.role if respondent else "Unknown",
        title=item.title,
        description=item.description,
        category=item.category,
        frequency_per_week=item.frequency_per_week,
        minutes_per_occurrence=item.minutes_per_occurrence,
        people_affected=item.people_affected,
        systems_involved=item.systems_involved,
        current_workaround=item.current_workaround,
        failure_modes=item.failure_modes,
        success_definition=item.success_definition,
        sensitive_flag=item.sensitive_flag,
        redaction_notes=item.redaction_notes,
        transcript_redacted=interview.transcript_redacted if interview and not item.sensitive_flag else None,
        summary_text=interview.summary_text if interview else "",
        score_id=score.id if score else None,
        impact_hours_per_week=score.impact_hours_per_week if score else None,
        effort_score=score.effort_score if score else None,
        confidence_score=score.confidence_score if score else None,
        priority_score=score.priority_score if score else None,
        quick_win=score.quick_win if score else False,
        automation_type=score.automation_type if score else None,
        suggested_solution=score.suggested_solution if score else None,
        owner_suggestion=score.owner_suggestion if score else None,
        created_at=item.created_at,
    )


@router.post("", response_model=PainPointRead)
def create_pain_point(payload: PainPointCreate, session: Session = Depends(get_session)) -> PainPoint:
    pain_point = PainPoint(**payload.model_dump())
    session.add(pain_point)
    session.flush()
    upsert_score(session, pain_point)
    session.commit()
    session.refresh(pain_point)
    return pain_point


@router.patch("/{pain_point_id}", response_model=PainPointRead)
def update_pain_point(pain_point_id: int, payload: PainPointUpdate, session: Session = Depends(get_session)) -> PainPoint:
    pain_point = session.get(PainPoint, pain_point_id)
    if pain_point is None:
        raise HTTPException(status_code=404, detail="Pain point not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(pain_point, field, value)

    session.add(pain_point)
    session.flush()
    upsert_score(session, pain_point)
    session.commit()
    session.refresh(pain_point)
    return pain_point


@router.delete("/{pain_point_id}")
def delete_pain_point(pain_point_id: int, session: Session = Depends(get_session)) -> dict[str, bool]:
    pain_point = session.get(PainPoint, pain_point_id)
    if pain_point is None:
        raise HTTPException(status_code=404, detail="Pain point not found")

    session.delete(pain_point)
    session.commit()
    return {"ok": True}
