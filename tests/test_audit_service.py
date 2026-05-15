"""Tests for the audit writer service."""
import pytest
from sqlalchemy import select
from app.services.audit.writer import write_audit
from app.models.audit_log import AuditLog


class TestAuditWriter:
    """Tests for write_audit — DB-backed, requires db_session."""

    async def test_write_audit_creates_entry(self, db_session):
        await write_audit(db_session, "document", "doc-123", "created")
        stmt = select(AuditLog).where(AuditLog.entity_id == "doc-123")
        entries = (await db_session.execute(stmt)).scalars().all()
        assert len(entries) == 1
        e = entries[0]
        assert e.entity_type == "document"
        assert e.entity_id == "doc-123"
        assert e.action == "created"
        assert e.created_at is not None

    async def test_write_audit_with_details(self, db_session):
        details = {"filename": "test.pdf", "size": 1234, "hash": "abc123"}
        await write_audit(db_session, "document", "doc-456", "uploaded", details=details)
        stmt = select(AuditLog).where(AuditLog.entity_id == "doc-456")
        entry = (await db_session.execute(stmt)).scalar_one()
        assert entry.details == details

    async def test_write_audit_without_details(self, db_session):
        await write_audit(db_session, "tax_session", "session-1", "created")
        stmt = select(AuditLog).where(AuditLog.entity_id == "session-1")
        entry = (await db_session.execute(stmt)).scalar_one()
        assert entry.details is None or entry.details == {}

    async def test_write_audit_persists_after_commit(self, db_session):
        await write_audit(db_session, "tax_item", "item-789", "classified",
                          details={"category": "salary_wages"})
        await db_session.commit()
        # Verify across a new session
        async with db_session.bind.connect() as conn:
            result = await conn.execute(
                select(AuditLog).where(AuditLog.entity_id == "item-789")
            )
            entry = result.scalar_one()
            assert entry.action == "classified"
            assert entry.details["category"] == "salary_wages"
