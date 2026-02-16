from datetime import datetime

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatContext(BaseModel):
    name: str | None = None
    email: str | None = None
    team: str = "COO Office"
    role: str = "COO"
    location: str | None = None
    consent: bool = False


class COOChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(default_factory=list)
    context: ChatContext = Field(default_factory=ChatContext)
    add_to_report: bool = False


class COOChatResponse(BaseModel):
    assistant_message: str
    needs_more_info: bool
    valid_concern: bool
    root_cause: str | None = None
    rationale: str
    category: str = "other"
    estimated_impact_hours_per_week: float = 0.0
    added_to_report: bool = False
    interview_id: int | None = None
    respondent_id: int | None = None
    pain_point_ids: list[int] = Field(default_factory=list)
    created_at: datetime
