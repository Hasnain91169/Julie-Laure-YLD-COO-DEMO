from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.adapters.internal import InternalIntakeAdapter
from app.adapters.vapi import VapiIntakeAdapter
from app.db import get_session
from app.schemas.intake import IntakeResponse
from app.schemas.payloads import InternalIntakePayload, VapiIntakePayload
from app.services.ingestion import IntakeIngestionService

router = APIRouter(prefix="/intake", tags=["intake"])
ingestion_service = IntakeIngestionService()


@router.post("/vapi", response_model=IntakeResponse)
async def intake_vapi(payload: VapiIntakePayload, session: Session = Depends(get_session)) -> IntakeResponse:
    canonical = VapiIntakeAdapter().to_canonical(payload.model_dump())
    interview_id, respondent_id, pain_point_ids = await ingestion_service.ingest(session, canonical)
    return IntakeResponse(interview_id=interview_id, respondent_id=respondent_id, pain_point_ids=pain_point_ids)


@router.post("/internal", response_model=IntakeResponse)
async def intake_internal(payload: InternalIntakePayload, session: Session = Depends(get_session)) -> IntakeResponse:
    canonical = InternalIntakeAdapter().to_canonical(payload.model_dump())
    interview_id, respondent_id, pain_point_ids = await ingestion_service.ingest(session, canonical)
    return IntakeResponse(interview_id=interview_id, respondent_id=respondent_id, pain_point_ids=pain_point_ids)
