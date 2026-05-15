from datetime import datetime, timedelta, timezone
import hashlib

from sqlalchemy import select

from app.models.auth_session import AuthSession
from app.models.unlock_capability import UnlockCapability
from app.models.user import User


async def _get_workspace_id(async_client):
    ws = await async_client.get('/api/workspaces')
    assert ws.status_code == 200
    data = ws.json()
    assert data
    return data[0]['id']


async def test_revoked_session_cannot_access_sensitive_route(async_client, db_session):
    setup = await async_client.post('/api/auth/setup', json={'master_password': 'supersecure123'})
    assert setup.status_code == 200
    workspace_id = await _get_workspace_id(async_client)
    token = async_client.cookies.get('taxai_session')
    token_hash = hashlib.sha256(token.encode('utf-8')).hexdigest()

    row = await db_session.execute(select(AuthSession).where(AuthSession.session_token_hash == token_hash))
    sess = row.scalar_one()
    sess.revoked_at = datetime.now(timezone.utc)
    await db_session.commit()

    sensitive = await async_client.get(f'/api/workspaces/{workspace_id}/items')
    assert sensitive.status_code == 401


async def test_unlock_capability_expires(async_client, db_session):
    setup = await async_client.post('/api/auth/setup', json={'master_password': 'supersecure123'})
    assert setup.status_code == 200
    token = async_client.cookies.get('taxai_session')
    token_hash = hashlib.sha256(token.encode('utf-8')).hexdigest()

    cap_row = await db_session.execute(select(UnlockCapability).where(UnlockCapability.session_token_hash == token_hash))
    cap = cap_row.scalar_one()
    cap.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    await db_session.commit()

    workspace_id = await _get_workspace_id(async_client)
    sensitive = await async_client.get(f'/api/workspaces/{workspace_id}/items')
    assert sensitive.status_code == 423


async def test_logout_revokes_capability(async_client, db_session):
    setup = await async_client.post('/api/auth/setup', json={'master_password': 'supersecure123'})
    assert setup.status_code == 200
    token = async_client.cookies.get('taxai_session')
    token_hash = hashlib.sha256(token.encode('utf-8')).hexdigest()

    out = await async_client.post('/api/auth/logout')
    assert out.status_code == 200

    cap_row = await db_session.execute(select(UnlockCapability).where(UnlockCapability.session_token_hash == token_hash))
    cap = cap_row.scalar_one_or_none()
    assert cap is not None
    assert cap.revoked_at is not None


async def test_password_reset_invalidates_old_capabilities(async_client, db_session):
    setup = await async_client.post('/api/auth/setup', json={'master_password': 'supersecure123'})
    assert setup.status_code == 200
    recovery_key = setup.json()['recovery_key']
    old_token = async_client.cookies.get('taxai_session')
    old_token_hash = hashlib.sha256(old_token.encode('utf-8')).hexdigest()

    reset = await async_client.post('/api/auth/recover-reset', json={'recovery_key': recovery_key, 'new_master_password': 'newsecure123'})
    assert reset.status_code == 200

    old_cap_row = await db_session.execute(select(UnlockCapability).where(UnlockCapability.session_token_hash == old_token_hash))
    old_cap = old_cap_row.scalar_one_or_none()
    assert old_cap is not None
    assert old_cap.revoked_at is not None

    ws = await _get_workspace_id(async_client)
    old_sensitive = await async_client.get(
        f'/api/workspaces/{ws}/items',
        headers={'Authorization': f'Bearer {old_token}'},
    )
    assert old_sensitive.status_code == 401


async def test_stale_key_epoch_blocked(async_client, db_session):
    setup = await async_client.post('/api/auth/setup', json={'master_password': 'supersecure123'})
    assert setup.status_code == 200
    workspace_id = await _get_workspace_id(async_client)

    user_row = await db_session.execute(select(User))
    user = user_row.scalar_one()
    user.unlock_epoch = user.unlock_epoch + 1
    await db_session.commit()

    sensitive = await async_client.get(f'/api/workspaces/{workspace_id}/items')
    assert sensitive.status_code in (401, 423)


async def test_capability_health_no_secrets(async_client):
    setup = await async_client.post('/api/auth/setup', json={'master_password': 'supersecure123'})
    assert setup.status_code == 200

    health = await async_client.get('/api/auth/capability-health')
    assert health.status_code == 200
    data = health.json()
    assert 'metrics' in data
    as_str = str(data).lower()
    assert 'password' not in as_str
    assert 'recovery_key' not in as_str
    assert 'session_token' not in as_str
