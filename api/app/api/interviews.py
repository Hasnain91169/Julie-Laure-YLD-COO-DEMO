from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_app_password
from app.db import get_session
from app.models.interview import Interview
from app.schemas.interview import InterviewCreate, InterviewRead, InterviewUpdate

router = APIRouter(prefix="/interviews", tags=["interviews"], dependencies=[Depends(require_app_password)])


@router.get("", response_model=list[InterviewRead])
def list_interviews(session: Session = Depends(get_session)) -> list[Interview]:
    return session.scalars(select(Interview).order_by(Interview.created_at.desc())).all()


@router.get("/{interview_id}", response_model=InterviewRead)
def get_interview(interview_id: int, session: Session = Depends(get_session)) -> Interview:
    interview = session.get(Interview, interview_id)
    if interview is None:
        raise HTTPException(status_code=404, detail="Interview not found")
    return interview


@router.post("", response_model=InterviewRead)
def create_interview(payload: InterviewCreate, session: Session = Depends(get_session)) -> Interview:
    interview = Interview(**payload.model_dump())
    session.add(interview)
    session.commit()
    session.refresh(interview)
    return interview


@router.patch("/{interview_id}", response_model=InterviewRead)
def update_interview(interview_id: int, payload: InterviewUpdate, session: Session = Depends(get_session)) -> Interview:
    interview = session.get(Interview, interview_id)
    if interview is None:
        raise HTTPException(status_code=404, detail="Interview not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(interview, field, value)

    session.add(interview)
    session.commit()
    session.refresh(interview)
    return interview


@router.delete("/{interview_id}")
def delete_interview(interview_id: int, session: Session = Depends(get_session)) -> dict[str, bool]:
    interview = session.get(Interview, interview_id)
    if interview is None:
        raise HTTPException(status_code=404, detail="Interview not found")
    session.delete(interview)
    session.commit()
    return {"ok": True}
