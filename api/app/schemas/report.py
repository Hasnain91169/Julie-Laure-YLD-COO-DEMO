from datetime import datetime
from typing import Any

from pydantic import BaseModel


class ReportRunResponse(BaseModel):
    id: int
    created_at: datetime
    source: str
    interview_id: int | None
    session_id: str | None
    pdf_path_or_url: str | None
    summary: str | None
    recommendations_json: str | None


class AttachReportRequest(BaseModel):
    interview_id: int | None = None
    session_id: str | None = None
    pdf_path_or_url: str | None = None
    summary: str | None = None
    recommendations_json: dict[str, Any] | None = None
    source: str = "n8n"
