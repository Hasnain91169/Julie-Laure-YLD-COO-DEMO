import random
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.enums import ChannelEnum, PainCategoryEnum
from app.models.interview import Interview
from app.models.pain_point import PainPoint
from app.models.respondent import Respondent
from app.services.redaction import redact_text
from app.services.scoring import upsert_score


TEAMS = [
    "People",
    "Finance",
    "Engineering",
    "Client Services",
    "Commercial",
]

ROLES = {
    "People": ["People Ops Manager", "HR Generalist", "Talent Lead"],
    "Finance": ["Finance Ops Analyst", "Controller", "Procurement Lead"],
    "Engineering": ["Engineering Manager", "Platform Lead", "Staff Engineer"],
    "Client Services": ["Delivery Lead", "Account Manager", "PMO Analyst"],
    "Commercial": ["Sales Ops Manager", "Revenue Analyst", "Partnerships Lead"],
}

PAIN_TEMPLATES = [
    {
        "title": "Manual onboarding checklist tracking",
        "description": "New joiner setup runs daily and takes 45 minutes per person across HR, IT and payroll tools.",
        "category": PainCategoryEnum.onboarding,
        "systems": ["Workday", "ServiceNow", "Google Sheets"],
        "frequency": 5,
        "minutes": 45,
        "people": 3,
    },
    {
        "title": "Invoice approval chasing across email",
        "description": "Finance spends 30 minutes per approval request, around 18 times a week, due to fragmented email threads.",
        "category": PainCategoryEnum.approvals,
        "systems": ["NetSuite", "Outlook", "Excel"],
        "frequency": 18,
        "minutes": 30,
        "people": 2,
    },
    {
        "title": "Weekly status report consolidation",
        "description": "Delivery leads copy data from Jira and Salesforce for weekly reports, 8 times per week at 50 minutes each.",
        "category": PainCategoryEnum.reporting,
        "systems": ["Jira", "Salesforce", "Excel"],
        "frequency": 8,
        "minutes": 50,
        "people": 4,
    },
    {
        "title": "Client escalations routed manually",
        "description": "Escalations are triaged in Slack and Teams by hand about 10 times per week, 20 minutes each.",
        "category": PainCategoryEnum.client_ops,
        "systems": ["Slack", "Teams", "ServiceNow"],
        "frequency": 10,
        "minutes": 20,
        "people": 3,
    },
    {
        "title": "Pipeline data mismatch",
        "description": "Commercial team reconciles CRM opportunities against forecast spreadsheets twice a day for 35 minutes.",
        "category": PainCategoryEnum.sales_ops,
        "systems": ["Salesforce", "HubSpot", "Excel"],
        "frequency": 10,
        "minutes": 35,
        "people": 5,
    },
    {
        "title": "Access provisioning delays",
        "description": "Access tickets take 25 minutes of manual updates, about 15 times weekly, causing onboarding delays.",
        "category": PainCategoryEnum.access_mgmt,
        "systems": ["Okta", "Jira", "ServiceNow"],
        "frequency": 15,
        "minutes": 25,
        "people": 2,
    },
    {
        "title": "Expense coding rework",
        "description": "Expense coding errors require 40 minutes of rework each time and happen 12 times per week.",
        "category": PainCategoryEnum.finance_ops,
        "systems": ["NetSuite", "SAP", "Excel"],
        "frequency": 12,
        "minutes": 40,
        "people": 3,
    },
    {
        "title": "Delivery handoff context loss",
        "description": "Project handoffs between sales and delivery trigger 60-minute clarification loops around 6 times weekly.",
        "category": PainCategoryEnum.comms,
        "systems": ["Notion", "Slack", "Salesforce"],
        "frequency": 6,
        "minutes": 60,
        "people": 4,
    },
]


def seed_demo_data(session: Session, interview_count: int = 24, reset: bool = False) -> dict[str, int]:
    if reset:
        session.query(PainPoint).delete()
        session.query(Interview).delete()
        session.query(Respondent).delete()
        session.commit()

    rng = random.Random(42)
    now = datetime.now(timezone.utc)

    respondents_created = 0
    interviews_created = 0
    pain_points_created = 0

    for idx in range(interview_count):
        team = TEAMS[idx % len(TEAMS)]
        role = rng.choice(ROLES[team])
        consent = rng.random() > 0.15

        respondent = Respondent(
            name=f"Respondent {idx + 1}",
            email=f"respondent{idx + 1}@example.com",
            team=team,
            role=role,
            location=rng.choice(["London", "New York", "Remote", "Lisbon"]),
            consent=consent,
        )
        session.add(respondent)
        session.flush()
        respondents_created += 1

        start = now - timedelta(days=rng.randint(0, 35), hours=rng.randint(1, 6))
        end = start + timedelta(minutes=rng.randint(18, 42))

        template = rng.choice(PAIN_TEMPLATES)
        transcript = (
            f"My name is {respondent.name}. We keep seeing friction: {template['description']} "
            "The current workaround is spreadsheets and manual follow-up. "
            "Success means the flow is automated with auditability and no duplicate entry."
        )

        interview = Interview(
            respondent_id=respondent.id,
            channel=rng.choice([ChannelEnum.vapi, ChannelEnum.internal]),
            started_at=start,
            ended_at=end,
            transcript_raw=transcript if consent else None,
            transcript_redacted=redact_text(transcript, respondent.name) if consent else None,
            summary_text=f"Key friction in {team}: {template['title']}.",
            metadata_json={"demo_mode": True, "seed_index": idx + 1},
        )
        session.add(interview)
        session.flush()
        interviews_created += 1

        entries = rng.randint(1, 2)
        for _ in range(entries):
            chosen = rng.choice(PAIN_TEMPLATES)
            pain_point = PainPoint(
                interview_id=interview.id,
                title=chosen["title"],
                description=chosen["description"],
                category=chosen["category"],
                frequency_per_week=float(chosen["frequency"] + rng.randint(-2, 2)),
                minutes_per_occurrence=float(chosen["minutes"] + rng.randint(-10, 8)),
                people_affected=max(1, chosen["people"] + rng.randint(-1, 2)),
                systems_involved=chosen["systems"],
                current_workaround="Manual spreadsheet and email follow-up",
                failure_modes="Delays, duplicate work, and inconsistent records",
                success_definition="Single workflow with traceable status and fewer manual steps",
                sensitive_flag=rng.random() < 0.12,
                redaction_notes="Mask client name and employee identities" if rng.random() < 0.25 else None,
            )
            session.add(pain_point)
            session.flush()
            upsert_score(session, pain_point)
            pain_points_created += 1

    session.commit()
    return {
        "respondents": respondents_created,
        "interviews": interviews_created,
        "pain_points": pain_points_created,
    }
