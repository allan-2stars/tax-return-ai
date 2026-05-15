"""Financial year helpers. Australian FY = 1 July – 30 June."""
from datetime import date, datetime

FY_BOUNDARIES: dict[str, tuple[date, date]] = {
    "2023-2024": (date(2023, 7, 1), date(2024, 6, 30)),
    "2024-2025": (date(2024, 7, 1), date(2025, 6, 30)),
    "2025-2026": (date(2025, 7, 1), date(2026, 6, 30)),
    "2026-2027": (date(2026, 7, 1), date(2027, 6, 30)),
}


def is_in_financial_year(d: date | str | None, fy: str) -> bool | None:
    """None if d is None. True/False if date is within the FY. Raises ValueError for unknown FY."""
    if d is None:
        return None
    if isinstance(d, str):
        d = datetime.strptime(d, "%Y-%m-%d").date()
    if fy not in FY_BOUNDARIES:
        raise ValueError(f"Unknown financial year: {fy!r}")
    start, end = FY_BOUNDARIES[fy]
    return start <= d <= end


def fy_label(fy: str) -> str:
    """'2025-2026' → '1 July 2025 – 30 June 2026'"""
    start, end = FY_BOUNDARIES[fy]
    return f"{start.strftime('%-d %B %Y')} – {end.strftime('%-d %B %Y')}"


def current_fy() -> str:
    today = date.today()
    year = today.year if today.month >= 7 else today.year - 1
    return f"{year}-{year + 1}"


def fy_warning(date_str: str | None, fy: str) -> str | None:
    """Return a warning string if date_str is outside fy, else None."""
    result = is_in_financial_year(date_str, fy)
    if result is False:
        return f"Date {date_str} is outside FY {fy} ({fy_label(fy)})."
    return None
