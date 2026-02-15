from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_app_password
from app.db import get_session
from app.models.score import Score
from app.schemas.score import ScoreRead, ScoreRecomputeRequest
from app.services.scoring import recompute_scores

router = APIRouter(prefix="/scores", tags=["scores"], dependencies=[Depends(require_app_password)])


@router.get("/{pain_point_id}", response_model=ScoreRead)
def get_score(pain_point_id: int, session: Session = Depends(get_session)) -> Score:
    score = session.scalar(select(Score).where(Score.pain_point_id == pain_point_id))
    if score is None:
        raise HTTPException(status_code=404, detail="Score not found")
    return score


@router.post("/recompute", response_model=list[ScoreRead])
def recompute(payload: ScoreRecomputeRequest, session: Session = Depends(get_session)) -> list[Score]:
    return recompute_scores(session, payload.pain_point_id)
