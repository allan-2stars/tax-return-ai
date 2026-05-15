import pytest
from sqlalchemy import select
from app.models.user import User
from app.services.security.key_cache import get_session_key


async def test_setup_status_initial(async_client):
    res = await async_client.get('/api/auth/setup-status')
    assert res.status_code == 200
    data = res.json()
    assert data['is_configured'] is False
    assert data['auth_mode'] == 'local'


async def test_setup_first_user_success(async_client):
    res = await async_client.post('/api/auth/setup', json={'master_password': 'supersecure123'})
    assert res.status_code == 200
    data = res.json()
    assert data['recovery_key']
    assert data['app_state'] == 'UNLOCKED'


async def test_second_setup_blocked(async_client):
    first = await async_client.post('/api/auth/setup', json={'master_password': 'supersecure123'})
    assert first.status_code == 200

    second = await async_client.post('/api/auth/setup', json={'master_password': 'anotherpass123'})
    assert second.status_code == 409


async def test_unlock_success_failure(async_client):
    res = await async_client.post('/api/auth/setup', json={'master_password': 'supersecure123'})
    assert res.status_code == 200

    bad = await async_client.post('/api/auth/unlock', json={'master_password': 'wrong-password'})
    assert bad.status_code == 401

    ok = await async_client.post('/api/auth/unlock', json={'master_password': 'supersecure123'})
    assert ok.status_code == 200
    assert ok.json()['app_state'] == 'UNLOCKED'


async def test_logout_revokes_session(async_client):
    setup = await async_client.post('/api/auth/setup', json={'master_password': 'supersecure123'})
    assert setup.status_code == 200

    sess = await async_client.get('/api/auth/session')
    assert sess.status_code == 200
    assert sess.json()['is_authenticated'] is True

    out = await async_client.post('/api/auth/logout')
    assert out.status_code == 200

    sess2 = await async_client.get('/api/auth/session')
    assert sess2.status_code == 200
    assert sess2.json()['is_authenticated'] is False


async def test_workspaces_require_auth(async_client):
    res = await async_client.get('/api/workspaces')
    assert res.status_code == 401


async def test_workspace_list_and_create(async_client):
    setup = await async_client.post('/api/auth/setup', json={'master_password': 'supersecure123'})
    assert setup.status_code == 200

    listed = await async_client.get('/api/workspaces')
    assert listed.status_code == 200
    data = listed.json()
    assert any(w['tax_year'] == 'FY2025' for w in data)
    assert any(w['tax_year'] == 'FY2024' for w in data)

    created = await async_client.post('/api/workspaces', json={'tax_year': 'FY2023', 'label': 'FY2023 Workspace'})
    assert created.status_code == 200
    c = created.json()
    assert c['tax_year'] == 'FY2023'


async def test_setup_creates_wrapped_dek(async_client, db_session):
    res = await async_client.post('/api/auth/setup', json={'master_password': 'supersecure123'})
    assert res.status_code == 200
    row = await db_session.execute(select(User))
    user = row.scalar_one()
    assert user.encrypted_dek_by_password is not None
    assert user.encrypted_dek_by_recovery is not None
    assert user.dek_version is not None


async def test_recovery_reset_preserves_access(async_client, db_session):
    setup = await async_client.post('/api/auth/setup', json={'master_password': 'supersecure123'})
    assert setup.status_code == 200
    recovery_key = setup.json()['recovery_key']

    reset = await async_client.post(
        '/api/auth/recover-reset',
        json={'recovery_key': recovery_key, 'new_master_password': 'newsecure123'},
    )
    assert reset.status_code == 200

    old_unlock = await async_client.post('/api/auth/unlock', json={'master_password': 'supersecure123'})
    assert old_unlock.status_code == 401
    new_unlock = await async_client.post('/api/auth/unlock', json={'master_password': 'newsecure123'})
    assert new_unlock.status_code == 200


async def test_logout_clears_cached_key(async_client):
    setup = await async_client.post('/api/auth/setup', json={'master_password': 'supersecure123'})
    assert setup.status_code == 200
    token = async_client.cookies.get('taxai_session')
    assert get_session_key(token) is not None
    out = await async_client.post('/api/auth/logout')
    assert out.status_code == 200
    assert get_session_key(token) is None
