"""Input sanitization utilities — prevents XSS and injection."""
import re


def strip_html(text: str | None) -> str | None:
    """Remove HTML tags from user-provided text."""
    if text is None:
        return None
    return re.sub(r"<[^>]*>", "", text)


def sanitize_session_title(title: str | None) -> str | None:
    """Sanitize session title — strip HTML, limit length."""
    if title is None:
        return None
    cleaned = strip_html(title)
    return cleaned[:255] if cleaned else None


def sanitize_description(desc: str | None) -> str | None:
    """Sanitize item description."""
    if desc is None:
        return None
    return strip_html(desc)
