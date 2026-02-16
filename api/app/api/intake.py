from uuid import uuid4

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.adapters.internal import InternalIntakeAdapter
from app.adapters.vapi import VapiIntakeAdapter
from app.api.deps import require_webhook_secret
from app.config import get_settings
from app.db import get_session
from app.models.respondent import Respondent
from app.schemas.intake import IntakeResponse, SessionRequest, SessionResponse
from app.schemas.payloads import InternalIntakePayload, VapiIntakePayload
from app.services.ingestion import IntakeIngestionService

router = APIRouter(prefix="/intake", tags=["intake"])
ingestion_service = IntakeIngestionService()


@router.post("/vapi", response_model=IntakeResponse)
async def intake_vapi(
    payload: VapiIntakePayload,
    session: Session = Depends(get_session),
    _: None = Depends(lambda: require_webhook_secret(get_settings().vapi_webhook_secret)),
) -> IntakeResponse:
    canonical = VapiIntakeAdapter().to_canonical(payload.model_dump())
    interview_id, respondent_id, pain_point_ids = await ingestion_service.ingest(session, canonical)
    return IntakeResponse(interview_id=interview_id, respondent_id=respondent_id, pain_point_ids=pain_point_ids)


@router.post("/internal", response_model=IntakeResponse)
async def intake_internal(payload: InternalIntakePayload, session: Session = Depends(get_session)) -> IntakeResponse:
    canonical = InternalIntakeAdapter().to_canonical(payload.model_dump())
    interview_id, respondent_id, pain_point_ids = await ingestion_service.ingest(session, canonical)
    return IntakeResponse(interview_id=interview_id, respondent_id=respondent_id, pain_point_ids=pain_point_ids)


@router.post("/session", response_model=SessionResponse)
def create_session(request: SessionRequest, session: Session = Depends(get_session)) -> SessionResponse:
    """Create a session for voice intake before VAPI call starts.

    Creates or updates a respondent record and returns a session_id that can be
    included in the VAPI call metadata.
    """
    # Try to find existing respondent by email if provided
    respondent = None
    if request.email:
        respondent = session.scalar(select(Respondent).where(Respondent.email == request.email))

    if respondent is None:
        # Create new respondent
        respondent = Respondent(
            name=request.name,
            email=request.email,
            team=request.team,
            role=request.role,
            location=request.location,
            consent=request.consent,
        )
        session.add(respondent)
    else:
        # Update existing respondent with new info
        if request.name:
            respondent.name = request.name
        respondent.team = request.team
        respondent.role = request.role
        if request.location:
            respondent.location = request.location
        respondent.consent = request.consent

    session.commit()
    session.refresh(respondent)

    # Generate unique session_id
    session_id = str(uuid4())

    return SessionResponse(session_id=session_id, respondent_id=respondent.id)
