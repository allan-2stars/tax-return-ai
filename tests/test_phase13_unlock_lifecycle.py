import hashlib
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.config import settings
from app.models.auth_session import AuthSession
from app.models.audit_log import AuditLog
from app.services.security.key_cache import clear_session_key, get_session_key


async def test_idle_auto_lock_expires_session_and_clears_key(async_client, db_session):
    setup = await async_client.post('/api/auth/setup', json={'master_password': 'supersecure123'})
    assert setup.status_code == 200
    token = async_client.cookies.get('taxai_session')
    assert token is not None
    assert get_session_key(token) is not None

    token_hash = hashlib.sha256(token.encode('utf-8')).hexdigest()
    row = await db_session.execute(select(AuthSession).where(AuthSession.session_token_hash == token_hash))
    sess = row.scalar_one()
    sess.last_seen_at = datetime.now(timezone.utc) - timedelta(minutes=120)
    await db_session.commit()

    old_idle = settings.session_idle_timeout_minutes
    settings.session_idle_timeout_minutes = 15
    try:
        session_status = await async_client.get('/api/auth/session')
    finally:
        settings.session_idle_timeout_minutes = old_idle

    assert session_status.status_code == 200
    assert session_status.json()['is_authenticated'] is False
    assert session_status.json()['app_state'] == 'SESSION_EXPIRED'
    assert get_session_key(token) is None

    audit = await db_session.execute(
        select(AuditLog).where(AuditLog.action == 'auto_lock_triggered').order_by(AuditLog.created_at.desc())
    )
    assert audit.scalar_one_or_none() is not None


async def test_locked_sensitive_workspace_route_returns_423(async_client):
    setup = await async_client.post('/api/auth/setup', json={'master_password': 'supersecure123'})
    assert setup.status_code == 200

    workspaces = await async_client.get('/api/workspaces')
    assert workspaces.status_code == 200
    workspace_id = workspaces.json()[0]['id']

    token = async_client.cookies.get('taxai_session')
    clear_session_key(token)

    items = await async_client.get(f'/api/workspaces/{workspace_id}/items')
    assert items.status_code == 423


async def test_unlock_restores_locked_workspace_access(async_client):
    setup = await async_client.post('/api/auth/setup', json={'master_password': 'supersecure123'})
    assert setup.status_code == 200

    workspaces = await async_client.get('/api/workspaces')
    workspace_id = workspaces.json()[0]['id']

    token = async_client.cookies.get('taxai_session')
    clear_session_key(token)

    locked = await async_client.get(f'/api/workspaces/{workspace_id}/items')
    assert locked.status_code == 423

    unlock = await async_client.post('/api/auth/unlock', json={'master_password': 'supersecure123'})
    assert unlock.status_code == 200

    unlocked = await async_client.get(f'/api/workspaces/{workspace_id}/items')
    assert unlocked.status_code == 200


async def test_password_reset_invalidates_old_session_token(async_client):
    setup = await async_client.post('/api/auth/setup', json={'master_password': 'supersecure123'})
    assert setup.status_code == 200
    recovery_key = setup.json()['recovery_key']
    old_token = async_client.cookies.get('taxai_session')

    reset = await async_client.post(
        '/api/auth/recover-reset',
        json={'recovery_key': recovery_key, 'new_master_password': 'newsecure123'},
    )
    assert reset.status_code == 200

    old_token_session = await async_client.get(
        '/api/auth/session',
        headers={'Authorization': f'Bearer {old_token}'},
    )
    assert old_token_session.status_code == 200
    assert old_token_session.json()['is_authenticated'] is False
