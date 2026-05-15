"""
Seed synthetic demo data into the database.

Produces 5 items covering all risk levels and review statuses:
  1. salary_wages  · income       · low    · auto_classified
  2. tools_equipment · deduction  · medium · needs_user_review
  3. work_from_home · deduction   · medium · needs_user_review
  4. out_of_scope   · out_of_scope· high   · needs_tax_agent_review
  5. duplicate_document · deduction · high · needs_user_review (same hash as item 2)

Idempotent: skips if "demo" session already exists.
Uses the API directly (HTTP client) so it works both inside and outside Docker.

Usage:
    python scripts/seed_demo.py                      # uses http://localhost:8010
    API_URL=http://localhost:8000 python scripts/seed_demo.py
"""
import os
import sys
import httpx

API_URL = os.getenv("API_URL", "http://localhost:8010")
TIMEOUT = 15.0
RETRY_COUNT = 10
RETRY_DELAY = 2


def _wait_for_api():
    """Wait until the API is reachable, with backoff."""
    import time as _time
    for attempt in range(1, RETRY_COUNT + 1):
        try:
            resp = httpx.get(f"{API_URL}/api/sessions", timeout=5)
            return
        except (httpx.ConnectError, httpx.TimeoutException):
            if attempt < RETRY_COUNT:
                print(f"  ⏳ Waiting for API at {API_URL} (attempt {attempt}/{RETRY_COUNT})...")
                _time.sleep(RETRY_DELAY)
    raise SystemExit(f"  ✗ API at {API_URL} not reachable after {RETRY_COUNT} attempts")


def api(path: str, method: str = "GET", json: dict | None = None) -> dict | list | None:
    """Make an API call and return parsed JSON."""
    url = f"{API_URL}{path}"
    resp = httpx.request(method, url, json=json, timeout=TIMEOUT)
    resp.raise_for_status()
    if resp.status_code == 204:
        return None
    return resp.json()


def main():
    _wait_for_api()
    # Check if demo session already exists
    sessions = api("/api/sessions")
    existing = [s for s in sessions if s.get("title") == "Demo - FY2025-2026"]
    if existing:
        print(f"Demo session already exists: {existing[0]['id']}")
        print("Run `make reset-db && make migrate && python scripts/seed_demo.py` to recreate.")
        return

    # 1. Create session
    session = api("/api/sessions", "POST", {
        "title": "Demo - FY2025-2026",
        "financial_year": "2025-2026",
        "notes": "Synthetic demo data for testing. All data is fictional."
    })
    sid = session["id"]
    print(f"  ✓ Created session: {sid}")

    # 2. Create documents for each item
    doc_income = api("/api/documents", "POST", {
        "session_id": sid,
        "original_filename": "income-statement-fy2526.pdf",
        "mime_type": "application/pdf",
        "file_size_bytes": 48500,
        "file_hash": "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1",
        "category": "income_statement",
        "financial_year": "2025-2026",
        "status": "processed",
    })
    did_income = doc_income["id"]
    print(f"  ✓ Created document: income-statement-fy2526.pdf")

    doc_tools = api("/api/documents", "POST", {
        "session_id": sid,
        "original_filename": "officeworks-receipt-march.pdf",
        "mime_type": "application/pdf",
        "file_size_bytes": 12300,
        "file_hash": "b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2",
        "category": "receipt",
        "financial_year": "2025-2026",
        "status": "processed",
    })
    did_tools = doc_tools["id"]

    # Same hash = duplicate_document (item 5 uses same hash)
    doc_tools_dup = api("/api/documents", "POST", {
        "session_id": sid,
        "original_filename": "officeworks-receipt-copy.pdf",
        "mime_type": "application/pdf",
        "file_size_bytes": 12300,
        "file_hash": "b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2",
        "category": "receipt",
        "financial_year": "2025-2026",
        "status": "duplicate_detected",
    })
    did_tools_dup = doc_tools_dup["id"]
    print(f"  ✓ Created document: officeworks-receipt-copy.pdf (duplicate)")

    doc_wfh = api("/api/documents", "POST", {
        "session_id": sid,
        "original_filename": "electricity-bill-q3.pdf",
        "mime_type": "application/pdf",
        "file_size_bytes": 8900,
        "file_hash": "c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3",
        "category": "utility_bill",
        "financial_year": "2025-2026",
        "status": "processed",
    })
    did_wfh = doc_wfh["id"]
    print(f"  ✓ Created document: electricity-bill-q3.pdf")

    doc_bas = api("/api/documents", "POST", {
        "session_id": sid,
        "original_filename": "bas-statement-march.pdf",
        "mime_type": "application/pdf",
        "file_size_bytes": 32500,
        "file_hash": "d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4",
        "category": "bas_statement",
        "financial_year": "2025-2026",
        "status": "processed",
    })
    did_bas = doc_bas["id"]
    print(f"  ✓ Created document: bas-statement-march.pdf")

    # 3. Create tax items
    # Item 1: salary_wages · income · low · auto_classified
    i1 = api("/api/items", "POST", {
        "session_id": sid,
        "item_type": "income",
        "category": "salary_wages",
        "amount": 95000.0,
        "description": "Annual salary — Acme Pty Ltd. Gross $95,000 with PAYG withholding of $24,367.",
        "confidence": 0.97,
        "needs_review": False,
        "review_reason": None,
        "ato_reference_hint": "Salary/Wages",
    })
    print(f"  ✓ Item 1: salary_wages ($95,000)")

    # Item 2: tools_equipment · deduction · medium · needs_user_review
    i2 = api("/api/items", "POST", {
        "session_id": sid,
        "item_type": "deduction",
        "category": "tools_equipment",
        "amount": 149.0,
        "description": "USB hub ($89) and keyboard ($60) from Officeworks for home office setup.",
        "confidence": 0.68,
        "needs_review": True,
        "review_reason": "Work-use percentage not confirmed. Possible private use component.",
        "ato_reference_hint": "D5",
    })
    print(f"  ✓ Item 2: tools_equipment ($149 — needs review)")

    # Item 3: work_from_home · deduction · medium · needs_user_review
    i3 = api("/api/items", "POST", {
        "session_id": sid,
        "item_type": "deduction",
        "category": "work_from_home",
        "amount": 520.0,
        "description": "Electricity bill ($200/qtr) — estimated WFH share. 3 days/week home office.",
        "confidence": 0.65,
        "needs_review": True,
        "review_reason": "Work-use percentage and reimbursement status not confirmed.",
        "ato_reference_hint": "D5",
    })
    print(f"  ✓ Item 3: work_from_home ($520 — needs review)")

    # Item 4: out_of_scope · out_of_scope · high · needs_tax_agent_review
    i4 = api("/api/items", "POST", {
        "session_id": sid,
        "item_type": "out_of_scope",
        "category": "out_of_scope",
        "amount": None,
        "description": "BAS statement detected — suggests business or GST activity beyond individual salary earner scope.",
        "confidence": 0.85,
        "needs_review": True,
        "review_reason": "BAS/GST language detected. May indicate sole trader or business income requiring registered tax agent review.",
        "ato_reference_hint": None,
    })
    print(f"  ✓ Item 4: out_of_scope (BAS — needs tax agent review)")

    # Item 5: duplicate_document · deduction · high · needs_user_review
    i5 = api("/api/items", "POST", {
        "session_id": sid,
        "item_type": "deduction",
        "category": "duplicate_document",
        "amount": 149.0,
        "description": "Same Officeworks receipt as Item 2 — identical file hash detected. Possible duplicate upload.",
        "confidence": 0.99,
        "needs_review": True,
        "review_reason": "File hash matches item 'officeworks-receipt-march.pdf'. User should confirm whether this is a genuine duplicate.",
        "ato_reference_hint": None,
    })
    print(f"  ✓ Item 5: duplicate_document ($149 — duplicate of item 2)")

    print(f"\n✅ Demo seed complete — 5 items in session {sid}")
    print(f"   Summary: {summarize(sid)}")


def summarize(sid: str) -> str:
    items = api(f"/api/items?session_id={sid}")
    income = [i for i in items if i["item_type"] == "income"]
    deductions = [i for i in items if i["item_type"] == "deduction"]
    out_of_scope = [i for i in items if i["item_type"] == "out_of_scope"]
    needs_review = [i for i in items if i["needs_review"]]
    total_income = sum(i["amount"] or 0 for i in income)
    total_deductions = sum(i["amount"] or 0 for i in deductions)
    return (
        f"{len(items)} items "
        f"(income: {len(income)} ${total_income:,.0f}, "
        f"deductions: {len(deductions)} ${total_deductions:,.0f}, "
        f"out_of_scope: {len(out_of_scope)}, "
        f"needs_review: {len(needs_review)})"
    )


if __name__ == "__main__":
    main()
