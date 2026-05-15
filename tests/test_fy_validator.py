"""Financial year boundary validation tests."""
import pytest
from app.constants.fy import is_in_financial_year, fy_label, current_fy


def test_date_in_fy():
    assert is_in_financial_year("2025-09-15", "2025-2026") is True


def test_date_before_fy():
    assert is_in_financial_year("2025-06-30", "2025-2026") is False


def test_date_after_fy():
    assert is_in_financial_year("2026-07-01", "2025-2026") is False


def test_date_fy_start_boundary():
    assert is_in_financial_year("2025-07-01", "2025-2026") is True


def test_date_fy_end_boundary():
    assert is_in_financial_year("2026-06-30", "2025-2026") is True


def test_none_date_returns_none():
    assert is_in_financial_year(None, "2025-2026") is None


def test_unknown_fy_raises():
    with pytest.raises(ValueError, match="Unknown financial year"):
        is_in_financial_year("2025-09-15", "1999-2000")


def test_fy_label():
    assert fy_label("2025-2026") == "1 July 2025 – 30 June 2026"


def test_current_fy_format():
    fy = current_fy()
    assert "-" in fy
    start, end = fy.split("-")
    assert int(end) == int(start) + 1
