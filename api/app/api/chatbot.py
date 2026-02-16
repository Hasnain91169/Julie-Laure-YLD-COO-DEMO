from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_app_password
from app.db import get_session
from app.schemas.chatbot import COOChatRequest, COOChatResponse
from app.services.coo_chat import COOChatService

router = APIRouter(prefix="/chatbot", tags=["chatbot"], dependencies=[Depends(require_app_password)])
service = COOChatService()


@router.post("/coo", response_model=COOChatResponse)
async def coo_chat(request: COOChatRequest, session: Session = Depends(get_session)) -> COOChatResponse:
    return await service.handle(session, request)
