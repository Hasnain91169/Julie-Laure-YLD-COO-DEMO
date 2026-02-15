from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.models.enums import ChannelEnum


class InterviewCreate(BaseModel):
    respondent_id: int
    channel: ChannelEnum
    started_at: datetime | None = None
    ended_at: datetime | None = None
    transcript_raw: str | None = None
    transcript_redacted: str | None = None
    summary_text: str
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class InterviewUpdate(BaseModel):
    started_at: datetime | None = None
    ended_at: datetime | None = None
    transcript_raw: str | None = None
    transcript_redacted: str | None = None
    summary_text: str | None = None
    metadata_json: dict[str, Any] | None = None


class InterviewRead(BaseModel):
    id: int
    respondent_id: int
    channel: ChannelEnum
    started_at: datetime | None
    ended_at: datetime | None
    transcript_raw: str | None
    transcript_redacted: str | None
    summary_text: str
    metadata_json: dict[str, Any]
    created_at: datetime

    model_config = {"from_attributes": True}
