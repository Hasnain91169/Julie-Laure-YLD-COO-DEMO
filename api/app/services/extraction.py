import re
from collections import Counter

from app.models.enums import PainCategoryEnum
from app.schemas.intake import CanonicalPainPoint

FRICTION_HINTS = (
    "manual",
    "approval",
    "wait",
    "delay",
    "copy",
    "paste",
    "reconcile",
    "error",
    "chase",
    "follow up",
    "spreadsheet",
    "excel",
    "onboarding",
    "invoice",
    "quote",
    "status",
    "handoff",
)

CATEGORY_KEYWORDS: dict[PainCategoryEnum, tuple[str, ...]] = {
    PainCategoryEnum.onboarding: ("onboard", "new joiner", "provision", "training"),
    PainCategoryEnum.approvals: ("approval", "sign off", "authorise", "authorize"),
    PainCategoryEnum.reporting: ("report", "dashboard", "kpi", "status update"),
    PainCategoryEnum.comms: ("slack", "email thread", "handoff", "communication"),
    PainCategoryEnum.finance_ops: ("invoice", "expense", "purchase order", "budget", "finance"),
    PainCategoryEnum.sales_ops: ("crm", "pipeline", "quote", "proposal", "salesforce", "hubspot"),
    PainCategoryEnum.client_ops: ("client", "account", "delivery", "qbr", "project status"),
    PainCategoryEnum.access_mgmt: ("access", "permission", "sso", "jira admin", "okta"),
}

SYSTEM_PATTERNS = {
    "Jira": r"\bjira\b",
    "Salesforce": r"\bsalesforce\b",
    "HubSpot": r"\bhubspot\b",
    "SAP": r"\bsap\b",
    "NetSuite": r"\bnetsuite\b",
    "Workday": r"\bworkday\b",
    "Slack": r"\bslack\b",
    "Teams": r"\bteams\b",
    "Excel": r"\bexcel\b|\bspreadsheet\b",
    "Google Sheets": r"\bsheets\b",
    "ServiceNow": r"\bservicenow\b",
    "Notion": r"\bnotion\b",
}


FREQUENCY_PATTERNS = [
    (re.compile(r"(\d+(?:\.\d+)?)\s*(?:times?)\s*(?:per|a)?\s*week", re.IGNORECASE), lambda m: float(m.group(1))),
    (re.compile(r"(\d+(?:\.\d+)?)\s*/\s*week", re.IGNORECASE), lambda m: float(m.group(1))),
    (re.compile(r"daily|every day", re.IGNORECASE), lambda _: 5.0),
    (re.compile(r"weekly|once a week", re.IGNORECASE), lambda _: 1.0),
    (re.compile(r"twice a week", re.IGNORECASE), lambda _: 2.0),
]

MINUTES_PATTERN = re.compile(r"(\d+(?:\.\d+)?)\s*(minutes?|mins?)", re.IGNORECASE)
HOURS_PATTERN = re.compile(r"(\d+(?:\.\d+)?)\s*(hours?|hrs?)", re.IGNORECASE)
PEOPLE_PATTERN = re.compile(r"(\d+)\s*(people|engineers|analysts|consultants|team members|staff)", re.IGNORECASE)


def infer_category(text: str) -> PainCategoryEnum:
    lowered = text.lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(keyword in lowered for keyword in keywords):
            return category
    return PainCategoryEnum.other


def infer_systems(text: str) -> list[str]:
    systems = [name for name, pattern in SYSTEM_PATTERNS.items() if re.search(pattern, text, re.IGNORECASE)]
    return systems


def infer_frequency_per_week(text: str) -> float:
    for pattern, resolver in FREQUENCY_PATTERNS:
        match = pattern.search(text)
        if match:
            return max(0.5, resolver(match))
    return 2.0


def infer_minutes(text: str) -> float:
    hour_match = HOURS_PATTERN.search(text)
    if hour_match:
        return float(hour_match.group(1)) * 60

    minute_match = MINUTES_PATTERN.search(text)
    if minute_match:
        return float(minute_match.group(1))

    return 30.0


def infer_people_affected(text: str) -> int:
    match = PEOPLE_PATTERN.search(text)
    if match:
        return max(1, int(match.group(1)))

    if "team" in text.lower():
        return 4
    return 1


def title_from_sentence(sentence: str) -> str:
    words = [w for w in re.split(r"\s+", sentence.strip()) if w]
    base = " ".join(words[:8]).strip(".,;:-")
    if not base:
        return "Operational friction"
    return base[0].upper() + base[1:]


def extract_pain_points_deterministic(transcript: str | None, summary: str | None) -> list[CanonicalPainPoint]:
    text = (transcript or "").strip()
    summary = (summary or "").strip()
    source = text or summary
    if not source:
        return []

    chunks = [s.strip() for s in re.split(r"[\n\r]+|(?<=[.!?])\s+", source) if s.strip()]
    candidates = [s for s in chunks if any(hint in s.lower() for hint in FRICTION_HINTS)]

    if not candidates and summary:
        candidates = [summary]
    elif not candidates and chunks:
        candidates = chunks[:1]

    pain_points: list[CanonicalPainPoint] = []
    seen: Counter[str] = Counter()
    for sentence in candidates[:8]:
        title = title_from_sentence(sentence)
        key = title.lower()
        seen[key] += 1
        if seen[key] > 1:
            continue

        pain_points.append(
            CanonicalPainPoint(
                title=title,
                description=sentence,
                category=infer_category(sentence),
                frequency_per_week=infer_frequency_per_week(sentence),
                minutes_per_occurrence=infer_minutes(sentence),
                people_affected=infer_people_affected(sentence),
                systems_involved=infer_systems(sentence),
                current_workaround="Manual follow-up and spreadsheet updates",
                failure_modes="Delays, missed updates, and inconsistent data",
                success_definition="Workflow is automated with clear ownership and visibility",
            )
        )

    return pain_points
