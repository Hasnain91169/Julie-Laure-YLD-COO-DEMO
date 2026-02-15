from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_app_password
from app.db import get_session
from app.schemas.views import DashboardMetrics
from app.services.analytics import dashboard_metrics

router = APIRouter(tags=["dashboard"], dependencies=[Depends(require_app_password)])


@router.get("/dashboard", response_model=DashboardMetrics)
def get_dashboard(session: Session = Depends(get_session)) -> dict:
    return dashboard_metrics(session)
