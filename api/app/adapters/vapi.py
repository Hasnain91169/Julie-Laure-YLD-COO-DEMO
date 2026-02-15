from typing import Any

from app.adapters.base import IntakeAdapter
from app.adapters.common import parse_extracted_pain_points
from app.models.enums import ChannelEnum
from app.schemas.intake import CanonicalIntake, CanonicalRespondent


class VapiIntakeAdapter(IntakeAdapter):
    def to_canonical(self, payload: dict[str, Any]) -> CanonicalIntake:
        respondent_payload = payload.get("respondent", {})
        return CanonicalIntake(
            channel=ChannelEnum.vapi,
            respondent=CanonicalRespondent(
                name=respondent_payload.get("name"),
                email=respondent_payload.get("email"),
                team=respondent_payload.get("team", "Unknown"),
                role=respondent_payload.get("role", "Unknown"),
                location=respondent_payload.get("location"),
                consent=bool(respondent_payload.get("consent", False)),
            ),
            started_at=payload.get("started_at"),
            ended_at=payload.get("ended_at"),
            transcript=payload.get("transcript"),
            call_summary=payload.get("call_summary") or "",
            extracted_pain_points=parse_extracted_pain_points(payload.get("extracted_fields")),
            metadata_json=payload.get("metadata_json") or {},
        )
