"""Audit helper — write audit log entries."""
import json
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.audit_log import AuditLog


async def write_audit(
    db: AsyncSession,
    entity_type: str,
    entity_id: str,
    action: str,
    changed_by: str = "system",
    details: dict | None = None,
) -> AuditLog:
    """Write an audit log entry and flush."""
    entry = AuditLog(
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        changed_by=changed_by,
        details=json.dumps(details) if details else None,
    )
    db.add(entry)
    await db.flush()
    return entry
