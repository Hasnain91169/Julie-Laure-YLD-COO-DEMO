import re

EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
PHONE_RE = re.compile(r"\b(?:\+?\d{1,2}[\s.-]?)?(?:\(?\d{3}\)?[\s.-]?)\d{3}[\s.-]?\d{4}\b")


def redact_text(text: str | None, respondent_name: str | None = None) -> str | None:
    if not text:
        return text

    redacted = EMAIL_RE.sub("[REDACTED_EMAIL]", text)
    redacted = PHONE_RE.sub("[REDACTED_PHONE]", redacted)

    if respondent_name:
        safe_name = respondent_name.strip()
        if safe_name:
            name_pattern = re.compile(re.escape(safe_name), re.IGNORECASE)
            redacted = name_pattern.sub("[REDACTED_NAME]", redacted)

    # Heuristic: redact "my name is X" snippets.
    redacted = re.sub(r"\b(my name is)\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?", r"\1 [REDACTED_NAME]", redacted, flags=re.IGNORECASE)
    return redacted
