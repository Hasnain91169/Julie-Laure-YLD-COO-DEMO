from typing import Any

from app.models.enums import PainCategoryEnum
from app.schemas.intake import CanonicalPainPoint


def parse_extracted_pain_points(raw_items: list[dict[str, Any]] | None) -> list[CanonicalPainPoint]:
    if not raw_items:
        return []

    parsed: list[CanonicalPainPoint] = []
    for item in raw_items:
        try:
            category_raw = (item.get("category") or "other").lower()
            category = PainCategoryEnum(category_raw) if category_raw in PainCategoryEnum._value2member_map_ else PainCategoryEnum.other
            parsed.append(
                CanonicalPainPoint(
                    title=item.get("title") or "Untitled pain point",
                    description=item.get("description") or item.get("detail") or "No description provided",
                    category=category,
                    frequency_per_week=float(item.get("frequency_per_week") or item.get("frequency") or 1),
                    minutes_per_occurrence=float(item.get("minutes_per_occurrence") or item.get("minutes") or 30),
                    people_affected=int(item.get("people_affected") or item.get("people") or 1),
                    systems_involved=[str(x) for x in (item.get("systems_involved") or item.get("systems") or [])],
                    current_workaround=item.get("current_workaround"),
                    failure_modes=item.get("failure_modes"),
                    success_definition=item.get("success_definition"),
                    sensitive_flag=bool(item.get("sensitive_flag", False)),
                    redaction_notes=item.get("redaction_notes"),
                )
            )
        except Exception:
            continue
    return parsed
