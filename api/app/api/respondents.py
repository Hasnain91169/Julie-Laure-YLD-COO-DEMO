from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_app_password
from app.db import get_session
from app.models.respondent import Respondent
from app.schemas.respondent import RespondentCreate, RespondentRead, RespondentUpdate

router = APIRouter(prefix="/respondents", tags=["respondents"], dependencies=[Depends(require_app_password)])


@router.get("", response_model=list[RespondentRead])
def list_respondents(session: Session = Depends(get_session)) -> list[Respondent]:
    return session.scalars(select(Respondent).order_by(Respondent.created_at.desc())).all()


@router.get("/{respondent_id}", response_model=RespondentRead)
def get_respondent(respondent_id: int, session: Session = Depends(get_session)) -> Respondent:
    respondent = session.get(Respondent, respondent_id)
    if respondent is None:
        raise HTTPException(status_code=404, detail="Respondent not found")
    return respondent


@router.post("", response_model=RespondentRead)
def create_respondent(payload: RespondentCreate, session: Session = Depends(get_session)) -> Respondent:
    respondent = Respondent(**payload.model_dump())
    session.add(respondent)
    session.commit()
    session.refresh(respondent)
    return respondent


@router.patch("/{respondent_id}", response_model=RespondentRead)
def update_respondent(respondent_id: int, payload: RespondentUpdate, session: Session = Depends(get_session)) -> Respondent:
    respondent = session.get(Respondent, respondent_id)
    if respondent is None:
        raise HTTPException(status_code=404, detail="Respondent not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(respondent, field, value)

    session.add(respondent)
    session.commit()
    session.refresh(respondent)
    return respondent


@router.delete("/{respondent_id}")
def delete_respondent(respondent_id: int, session: Session = Depends(get_session)) -> dict[str, bool]:
    respondent = session.get(Respondent, respondent_id)
    if respondent is None:
        raise HTTPException(status_code=404, detail="Respondent not found")
    session.delete(respondent)
    session.commit()
    return {"ok": True}
