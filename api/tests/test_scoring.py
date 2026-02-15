from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db import Base
from app.models.enums import ChannelEnum, PainCategoryEnum
from app.models.interview import Interview
from app.models.pain_point import PainPoint
from app.models.respondent import Respondent
from app.services.scoring import calculate_impact_hours_per_week, upsert_score


def build_session() -> Session:
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    return Session(bind=engine)


def test_impact_formula_matches_spec() -> None:
    session = build_session()

    respondent = Respondent(team="Engineering", role="Manager", consent=True)
    session.add(respondent)
    session.flush()

    interview = Interview(
        respondent_id=respondent.id,
        channel=ChannelEnum.internal,
        summary_text="summary",
        metadata_json={},
        started_at=datetime.now(timezone.utc),
        ended_at=datetime.now(timezone.utc),
    )
    session.add(interview)
    session.flush()

    pain_point = PainPoint(
        interview_id=interview.id,
        title="Manual reporting",
        description="Weekly manual reporting in Excel",
        category=PainCategoryEnum.reporting,
        frequency_per_week=10,
        minutes_per_occurrence=30,
        people_affected=4,
        systems_involved=["Excel", "Jira"],
    )
    session.add(pain_point)
    session.flush()

    impact = calculate_impact_hours_per_week(pain_point)
    assert impact == 20.0


def test_upsert_score_sets_priority_and_quick_win() -> None:
    session = build_session()

    respondent = Respondent(team="Finance", role="Analyst", consent=True)
    session.add(respondent)
    session.flush()

    interview = Interview(
        respondent_id=respondent.id,
        channel=ChannelEnum.vapi,
        summary_text="summary",
        metadata_json={},
        started_at=datetime.now(timezone.utc),
        ended_at=datetime.now(timezone.utc),
    )
    session.add(interview)
    session.flush()

    pain_point = PainPoint(
        interview_id=interview.id,
        title="Invoice approval delays",
        description="Invoice approval takes 30 minutes 20 times a week for 2 people",
        category=PainCategoryEnum.approvals,
        frequency_per_week=20,
        minutes_per_occurrence=30,
        people_affected=2,
        systems_involved=["NetSuite", "Outlook"],
        success_definition="Approval in one place",
    )
    session.add(pain_point)
    session.flush()

    score = upsert_score(session, pain_point)
    assert score.priority_score > 0
    assert score.impact_hours_per_week == 20.0
    assert score.quick_win is False
