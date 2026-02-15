from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import require_app_password
from app.db import get_session
from app.services.seed import seed_demo_data

router = APIRouter(prefix="/demo", tags=["demo"], dependencies=[Depends(require_app_password)])


@router.post("/seed")
def seed_demo(
    interview_count: int = Query(default=24, ge=20, le=200),
    reset: bool = Query(default=False),
    session: Session = Depends(get_session),
) -> dict[str, int]:
    return seed_demo_data(session, interview_count=interview_count, reset=reset)
