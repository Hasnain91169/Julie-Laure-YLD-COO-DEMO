from app.models.enums import PainCategoryEnum
from app.services.extraction import extract_pain_points_deterministic


def test_deterministic_extraction_reads_operational_signals() -> None:
    transcript = (
        "We manually compile weekly status reports in Jira and Excel 8 times per week, "
        "it takes 50 minutes each run for 4 people. "
        "Access approvals in ServiceNow happen daily and each takes 20 minutes."
    )
    items = extract_pain_points_deterministic(transcript, "")

    assert len(items) >= 2
    first = items[0]
    assert first.frequency_per_week >= 8
    assert first.minutes_per_occurrence >= 50
    assert first.people_affected >= 4
    assert "Jira" in first.systems_involved or "Excel" in first.systems_involved


def test_deterministic_extraction_falls_back_to_summary() -> None:
    summary = "Finance team spends 30 minutes on invoice approvals twice a week in NetSuite."
    items = extract_pain_points_deterministic(None, summary)

    assert len(items) == 1
    assert items[0].category in {PainCategoryEnum.finance_ops, PainCategoryEnum.approvals, PainCategoryEnum.other}
    assert items[0].minutes_per_occurrence >= 30
