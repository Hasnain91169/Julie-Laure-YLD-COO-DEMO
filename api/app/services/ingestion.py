import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.interview import Interview
from app.models.pain_point import PainPoint
from app.models.respondent import Respondent
from app.schemas.intake import CanonicalIntake
from app.services.ai_extractor import AIExtractor
from app.services.extraction import extract_pain_points_deterministic
from app.services.redaction import redact_text
from app.services.scoring import upsert_score


class IntakeIngestionService:
    def __init__(self) -> None:
        self.ai_extractor = AIExtractor()

    async def ingest(self, session: Session, canonical: CanonicalIntake) -> tuple[int, int, list[int]]:
        respondent = self._upsert_respondent(session, canonical)

        transcript_raw = canonical.transcript if respondent.consent else None
        transcript_redacted = redact_text(canonical.transcript, respondent.name) if canonical.transcript else None

        interview = Interview(
            respondent_id=respondent.id,
            channel=canonical.channel,
            started_at=canonical.started_at,
            ended_at=canonical.ended_at,
            transcript_raw=transcript_raw,
            transcript_redacted=transcript_redacted if respondent.consent else None,
            summary_text=canonical.call_summary,
            metadata_json=canonical.metadata_json,
        )
        session.add(interview)
        session.flush()

        extracted = canonical.extracted_pain_points
        if not extracted:
            ai_pain_points = await self.ai_extractor.extract(canonical.transcript, canonical.call_summary)
            extracted = ai_pain_points or extract_pain_points_deterministic(canonical.transcript, canonical.call_summary)

        pain_point_ids: list[int] = []
        for item in extracted:
            pain_point = PainPoint(
                interview_id=interview.id,
                title=item.title,
                description=item.description,
                category=item.category,
                frequency_per_week=max(0.1, item.frequency_per_week),
                minutes_per_occurrence=max(1.0, item.minutes_per_occurrence),
                people_affected=max(1, item.people_affected),
                systems_involved=item.systems_involved,
                current_workaround=item.current_workaround,
                failure_modes=item.failure_modes,
                success_definition=item.success_definition,
                sensitive_flag=item.sensitive_flag,
                redaction_notes=item.redaction_notes,
            )
            session.add(pain_point)
            session.flush()
            upsert_score(session, pain_point)
            pain_point_ids.append(pain_point.id)

        session.commit()
        session.refresh(respondent)
        session.refresh(interview)

        # Trigger n8n workflow if configured
        await self._trigger_n8n(interview.id, canonical.metadata_json.get("session_id"), respondent.id)

        return interview.id, respondent.id, pain_point_ids

    def _upsert_respondent(self, session: Session, canonical: CanonicalIntake) -> Respondent:
        incoming = canonical.respondent
        respondent = None
        if incoming.email:
            respondent = session.scalar(select(Respondent).where(Respondent.email == incoming.email))

        if respondent is None:
            respondent = Respondent(
                name=incoming.name,
                email=incoming.email,
                team=incoming.team,
                role=incoming.role,
                location=incoming.location,
                consent=incoming.consent,
            )
            session.add(respondent)
            session.flush()
            return respondent

        respondent.name = incoming.name or respondent.name
        respondent.team = incoming.team
        respondent.role = incoming.role
        respondent.location = incoming.location or respondent.location
        respondent.consent = incoming.consent
        session.add(respondent)
        session.flush()
        return respondent

    async def _trigger_n8n(self, interview_id: int, session_id: str | None, respondent_id: int) -> None:
        """Trigger n8n workflow after successful intake.

        Sends interview_id, session_id, and respondent_id to configured n8n webhook.
        Fails silently if n8n is not configured or unavailable.
        """
        settings = get_settings()
        if not settings.n8n_webhook_url:
            return

        try:
            async with httpx.AsyncClient(timeout=5) as client:
                await client.post(
                    settings.n8n_webhook_url,
                    json={"interview_id": interview_id, "session_id": session_id, "respondent_id": respondent_id},
                    headers={"x-webhook-secret": settings.n8n_webhook_secret or ""},
                )
        except Exception:
            # Don't fail intake if n8n is down
            pass
