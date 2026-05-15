"""
Generate a reviewable JSON export summary for a tax session.

Export is a reviewable data package — NOT a final tax return or ATO submission.
Includes disclaimers throughout.

Usage:
    python scripts/export_demo.py                               # exports latest "Demo" session
    python scripts/export_demo.py  <session_id>                 # export specific session
    python scripts/export_demo.py  --all                        # export all sessions
    API_URL=http://localhost:8000 python scripts/export_demo.py
"""
import json
import os
import sys
from datetime import datetime, timezone

import httpx

API_URL = os.getenv("API_URL", "http://localhost:8010")
EXPORT_DIR = os.getenv("EXPORT_DIR", "./data/exports")
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


def api(path: str, method: str = "GET", json_data: dict | None = None):
    url = f"{API_URL}{path}"
    resp = httpx.request(method, url, json=json_data, timeout=TIMEOUT)
    resp.raise_for_status()
    if resp.status_code == 204:
        return None
    return resp.json()


def generate_export(session_id: str) -> dict:
    """Generate a reviewable JSON export for a single session."""
    session = api(f"/api/sessions/{session_id}")
    documents = api(f"/api/documents?session_id={session_id}")
    items = api(f"/api/items?session_id={session_id}")
    audit_logs = api(f"/api/audit?entity_id={session_id}&limit=100")

    # Categorise items
    income_items = [i for i in items if i["item_type"] == "income"]
    deduction_items = [i for i in items if i["item_type"] == "deduction"]
    out_of_scope_items = [i for i in items if i["item_type"] == "out_of_scope"]
    offset_items = [i for i in items if i["item_type"] == "offset"]
    needs_review_items = [i for i in items if i["needs_review"]]
    approved_items = [i for i in items if not i["needs_review"]]

    total_income = sum(i["amount"] or 0 for i in income_items)
    total_deductions = sum(i["amount"] or 0 for i in deduction_items)
    total_offsets = sum(i["amount"] or 0 for i in offset_items)

    return {
        "export_metadata": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "tool": "tax-return-ai",
            "version": "0.1.0",
            "disclaimer": (
                "This is a DRAFT tax-ready data summary for review purposes only. "
                "It is NOT a final tax return, NOT ATO-approved, and does not constitute "
                "tax advice. All items are candidate classifications requiring human review. "
                "This document must be reviewed by the taxpayer and/or a registered tax agent "
                "before any lodgement."
            ),
            "export_type": "review_package",
            "status": "draft_only",
        },
        "session": {
            "id": session["id"],
            "title": session["title"],
            "financial_year": session["financial_year"],
            "status": session["status"],
            "notes": session["notes"],
            "created_at": session["created_at"],
        },
        "summary": {
            "total_documents": len(documents),
            "total_items": len(items),
            "income_count": len(income_items),
            "deduction_count": len(deduction_items),
            "offset_count": len(offset_items),
            "out_of_scope_count": len(out_of_scope_items),
            "needs_review_count": len(needs_review_items),
            "approved_count": len(approved_items),
            "total_income_aud": total_income,
            "total_candidate_deductions_aud": total_deductions,
            "total_offsets_aud": total_offsets,
        },
        "income_items": [
            {
                "id": i["id"],
                "category": i["category"],
                "amount": i["amount"],
                "description": i["description"],
                "confidence": i["confidence"],
                "status": "approved" if not i["needs_review"] else "needs_review",
                "review_reason": i["review_reason"],
            }
            for i in income_items
        ],
        "deduction_items": [
            {
                "id": i["id"],
                "category": i["category"],
                "amount": i["amount"],
                "description": i["description"],
                "confidence": i["confidence"],
                "status": "approved" if not i["needs_review"] else "needs_review",
                "review_reason": i["review_reason"],
                "ato_reference_hint": i["ato_reference_hint"],
            }
            for i in deduction_items
        ],
        "offsets": [
            {
                "id": i["id"],
                "category": i["category"],
                "amount": i["amount"],
                "description": i["description"],
            }
            for i in offset_items
        ],
        "needs_review_items": [
            {
                "id": i["id"],
                "type": i["item_type"],
                "category": i["category"],
                "amount": i["amount"],
                "description": i["description"],
                "review_reason": i["review_reason"],
            }
            for i in needs_review_items
        ],
        "out_of_scope_items": [
            {
                "id": i["id"],
                "category": i["category"],
                "description": i["description"],
                "review_reason": i["review_reason"],
                "recommendation": "Refer to a registered tax agent.",
            }
            for i in out_of_scope_items
        ],
        "source_documents": [
            {
                "id": d["id"],
                "filename": d["original_filename"],
                "mime_type": d["mime_type"],
                "size_bytes": d["file_size_bytes"],
                "status": d["status"],
            }
            for d in documents
        ],
        "audit_notes": [
            {
                "action": a["action"],
                "entity_type": a["entity_type"],
                "changed_by": a["changed_by"],
                "details": a["details"],
                "timestamp": a["created_at"],
            }
            for a in audit_logs
        ],
        "export_warnings": _generate_warnings(session, items, documents),
    }


def _generate_warnings(session: dict, items: list, documents: list) -> list:
    """Generate warnings about unresolved issues in this export."""
    warnings = []
    needs_review = [i for i in items if i["needs_review"]]
    failed_docs = [d for d in documents if d["status"] == "failed"]
    duplicates = [d for d in documents if d["status"] == "duplicate_detected"]

    if needs_review:
        warnings.append(
            f"{len(needs_review)} item(s) still marked as needs_review. "
            "These require user or tax-agent review before final lodgement."
        )
    if failed_docs:
        warnings.append(f"{len(failed_docs)} document(s) failed processing.")
    if duplicates:
        warnings.append(
            f"{len(duplicates)} duplicate document(s) detected. "
            "Review and confirm before proceeding."
        )
    warnings.append(
        "This is not a final tax return. Do not lodge this output directly. "
        "Have all items reviewed by the taxpayer or a registered tax agent."
    )
    return warnings


def save_export(session_id: str, data: dict, label: str) -> str:
    """Write export to file and return path."""
    os.makedirs(EXPORT_DIR, exist_ok=True)
    fy = data["session"]["financial_year"]
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"export_{label}_{fy}_{timestamp}.json"
    filepath = os.path.join(EXPORT_DIR, filename)
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2, default=str)
    return filepath


def log(data: dict):
    """Print a compact summary."""
    s = data["summary"]
    w = data["export_warnings"]
    print(f"\n{'='*60}")
    print(f"EXPORT: {data['session']['title']} ({data['session']['financial_year']})")
    print(f"{'='*60}")
    print(f"  Documents:      {s['total_documents']}")
    print(f"  Income items:   {s['income_count']}   ${s['total_income_aud']:>10,.0f}")
    print(f"  Deduction items:{s['deduction_count']}   ${s['total_candidate_deductions_aud']:>10,.0f}")
    print(f"  Offsets:        {s['offset_count']}")
    print(f"  Out of scope:   {s['out_of_scope_count']}")
    print(f"  Needs review:   {s['needs_review_count']}")
    print(f"  Approved:       {s['approved_count']}")
    print(f"  Warnings:       {len(w)}")
    for warn in w:
        print(f"    ⚠  {warn}")
    print(f"{'='*60}")
    print(f"  Status: DRAFT — for review only. Not a final tax return.")
    print(f"{'='*60}")


def main():
    _wait_for_api()
    args = sys.argv[1:]

    if "--all" in args:
        sessions = api("/api/sessions")
        print(f"Exporting all {len(sessions)} session(s)...")
        for s in sessions:
            data = generate_export(s["id"])
            path = save_export(s["id"], data, s["title"][:20].replace(" ", "_"))
            log(data)
            print(f"  Saved to: {path}")
        return

    if args and args[0] not in ("--all",):
        session_id = args[0]
    else:
        # Find latest demo session
        sessions = api("/api/sessions")
        if not sessions:
            print("No sessions found. Run `python scripts/seed_demo.py` first.")
            sys.exit(1)
        session_id = sessions[0]["id"]
        print(f"Exporting latest session: {sessions[0]['title']} ({session_id})")

    data = generate_export(session_id)
    path = save_export(session_id, data, data["session"]["title"][:20].replace(" ", "_"))
    log(data)
    print(f"  Saved to: {path}")
    print(f"\n  This is a draft review package. It is not a final tax return.")


if __name__ == "__main__":
    main()
