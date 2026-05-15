from pathlib import Path
from sqlalchemy import select

from app.models.export_package import ExportPackageModel
from app.models.tax_item import TaxItem
from app.models.tax_session import TaxSession
from app.models.tax_workspace import TaxWorkspace
from app.models.user import User


async def _setup_workspace(async_client):
    res = await async_client.post('/api/auth/setup', json={'master_password': 'supersecure123'})
    assert res.status_code == 200
    ws = await async_client.get('/api/workspaces')
    assert ws.status_code == 200
    return ws.json()[0]['id']


async def _ensure_session(async_client, db_session, workspace_id: str):
    ensure = await async_client.get(f'/api/workspaces/{workspace_id}/items')
    assert ensure.status_code == 200
    row = await db_session.execute(select(TaxSession).where(TaxSession.workspace_id == workspace_id))
    return row.scalar_one()


async def _seed_ready_item(db_session, session_id: str):
    item = TaxItem(
        session_id=session_id,
        item_type='deduction',
        category='tools_equipment',
        amount=55,
        description='tool',
        needs_review=False,
        review_status='confirmed',
    )
    db_session.add(item)
    await db_session.commit()


async def test_generate_requires_auth(async_client):
    res = await async_client.post('/api/workspaces/w1/review-pack/generate', json={'export_password': 'verystrongpass123', 'include_source_documents': False})
    assert res.status_code == 401


async def test_generate_wrong_workspace_blocked(async_client, db_session):
    workspace_id = await _setup_workspace(async_client)
    session = await _ensure_session(async_client, db_session, workspace_id)
    await _seed_ready_item(db_session, session.id)

    other_user = User(
        email='other@example.com',
        display_name='other',
        password_kdf='pbkdf2_sha256_600k',
        password_salt='salt',
        password_hash='hash',
        recovery_key_salt='salt',
        recovery_key_hash='hash',
        is_active=True,
    )
    db_session.add(other_user)
    await db_session.flush()
    other_workspace = TaxWorkspace(user_id=other_user.id, tax_year='FY2023', label='Other', status='active')
    db_session.add(other_workspace)
    await db_session.commit()

    blocked = await async_client.post(
        f'/api/workspaces/{other_workspace.id}/review-pack/generate',
        json={'export_password': 'verystrongpass123', 'include_source_documents': False},
    )
    assert blocked.status_code == 404


async def test_generate_not_ready_blocked(async_client, db_session):
    workspace_id = await _setup_workspace(async_client)
    session = await _ensure_session(async_client, db_session, workspace_id)
    item = TaxItem(
        session_id=session.id,
        item_type='deduction',
        category='tools_equipment',
        amount=55,
        description='tool',
        needs_review=True,
        review_status='needs_review',
    )
    db_session.add(item)
    await db_session.commit()

    blocked = await async_client.post(
        f'/api/workspaces/{workspace_id}/review-pack/generate',
        json={'export_password': 'verystrongpass123', 'include_source_documents': False},
    )
    assert blocked.status_code == 409


async def test_weak_password_rejected(async_client, db_session):
    workspace_id = await _setup_workspace(async_client)
    session = await _ensure_session(async_client, db_session, workspace_id)
    await _seed_ready_item(db_session, session.id)
    weak = await async_client.post(
        f'/api/workspaces/{workspace_id}/review-pack/generate',
        json={'export_password': 'password123', 'include_source_documents': False},
    )
    assert weak.status_code == 400


async def test_generate_ready_and_metadata_only(async_client, db_session):
    workspace_id = await _setup_workspace(async_client)
    session = await _ensure_session(async_client, db_session, workspace_id)
    await _seed_ready_item(db_session, session.id)

    res = await async_client.post(
        f'/api/workspaces/{workspace_id}/review-pack/generate',
        json={'export_password': 'verystrongpass123', 'include_source_documents': False},
    )
    assert res.status_code == 200
    data = res.json()
    assert data['encrypted'] is True
    assert data['format'] == 'enc_zip_v1'
    assert data['file_size'] > 0
    assert data['sha256']
    assert data['encryption_version'] == '1.0'
    assert data['kdf_params_summary']

    row = await db_session.execute(select(ExportPackageModel).where(ExportPackageModel.id == data['id']))
    rec = row.scalar_one()
    assert rec.export_data is None
    assert rec.storage_path
    assert Path(rec.storage_path).exists()


async def test_download_and_history(async_client, db_session):
    workspace_id = await _setup_workspace(async_client)
    session = await _ensure_session(async_client, db_session, workspace_id)
    await _seed_ready_item(db_session, session.id)

    gen = await async_client.post(
        f'/api/workspaces/{workspace_id}/review-pack/generate',
        json={'export_password': 'verystrongpass123', 'include_source_documents': False},
    )
    assert gen.status_code == 200
    export_id = gen.json()['id']

    hist = await async_client.get(f'/api/workspaces/{workspace_id}/review-pack')
    assert hist.status_code == 200
    assert len(hist.json()) >= 1
    assert 'export_data' not in hist.text

    dl = await async_client.get(f'/api/workspaces/{workspace_id}/review-pack/{export_id}/download')
    assert dl.status_code == 200
    assert dl.content
    row = await db_session.execute(select(ExportPackageModel).where(ExportPackageModel.id == export_id))
    rec = row.scalar_one()
    assert rec.downloaded_at is not None


async def test_wrong_workspace_cannot_download(async_client, db_session):
    workspace_id = await _setup_workspace(async_client)
    session = await _ensure_session(async_client, db_session, workspace_id)
    await _seed_ready_item(db_session, session.id)

    gen = await async_client.post(
        f'/api/workspaces/{workspace_id}/review-pack/generate',
        json={'export_password': 'verystrongpass123', 'include_source_documents': False},
    )
    assert gen.status_code == 200
    export_id = gen.json()['id']

    other_user = User(
        email='other@example.com',
        display_name='other',
        password_kdf='pbkdf2_sha256_600k',
        password_salt='salt',
        password_hash='hash',
        recovery_key_salt='salt',
        recovery_key_hash='hash',
        is_active=True,
    )
    db_session.add(other_user)
    await db_session.flush()
    other_workspace = TaxWorkspace(user_id=other_user.id, tax_year='FY2023', label='Other', status='active')
    db_session.add(other_workspace)
    await db_session.commit()

    blocked = await async_client.get(f'/api/workspaces/{other_workspace.id}/review-pack/{export_id}/download')
    assert blocked.status_code == 404


async def test_delete_review_pack(async_client, db_session):
    workspace_id = await _setup_workspace(async_client)
    session = await _ensure_session(async_client, db_session, workspace_id)
    await _seed_ready_item(db_session, session.id)
    gen = await async_client.post(
        f'/api/workspaces/{workspace_id}/review-pack/generate',
        json={'export_password': 'verystrongpass123', 'include_source_documents': False},
    )
    export_id = gen.json()['id']
    row = await db_session.execute(select(ExportPackageModel).where(ExportPackageModel.id == export_id))
    rec = row.scalar_one()
    path = Path(rec.storage_path)
    assert path.exists()
    deleted = await async_client.delete(f'/api/workspaces/{workspace_id}/review-pack/{export_id}')
    assert deleted.status_code == 200
    history = await async_client.get(f'/api/workspaces/{workspace_id}/review-pack')
    assert history.status_code == 200
    rec2 = next(r for r in history.json() if r['id'] == export_id)
    assert rec2['status'] == 'deleted'
    assert rec2['filename'] is not None
    assert not path.exists()


async def test_legacy_export_routes_locked_down(async_client):
    res = await async_client.get('/api/export/any-session-id')
    assert res.status_code in (401, 410)
