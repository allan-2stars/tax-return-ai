from sqlalchemy import select

from app.models.document import Document
from app.models.tax_item import TaxItem
from app.models.tax_session import TaxSession
from app.models.tax_workspace import TaxWorkspace
from app.models.user import User


async def _setup_and_get_workspace(async_client):
    res = await async_client.post('/api/auth/setup', json={'master_password': 'supersecure123'})
    assert res.status_code == 200
    ws = await async_client.get('/api/workspaces')
    assert ws.status_code == 200
    workspaces = ws.json()
    assert len(workspaces) >= 1
    return workspaces[0]['id']


async def test_workspace_routes_require_auth(async_client):
    unauth_docs = await async_client.get('/api/workspaces/w1/documents')
    assert unauth_docs.status_code == 401

    unauth_upload = await async_client.post(
        '/api/workspaces/w1/documents/upload',
        files={'file': ('a.pdf', b'%PDF-1.4', 'application/pdf')},
    )
    assert unauth_upload.status_code == 401

    unauth_items = await async_client.get('/api/workspaces/w1/items')
    assert unauth_items.status_code == 401

    unauth_export = await async_client.post('/api/workspaces/w1/review-pack')
    assert unauth_export.status_code == 401


async def test_list_documents_by_workspace(async_client, db_session):
    workspace_id = await _setup_and_get_workspace(async_client)

    docs = await async_client.get(f'/api/workspaces/{workspace_id}/documents')
    assert docs.status_code == 200

    session_result = await db_session.execute(
        select(TaxSession).where(TaxSession.workspace_id == workspace_id)
    )
    session = session_result.scalar_one_or_none()
    assert session is not None

    new_doc = Document(
        session_id=session.id,
        original_filename='receipt.pdf',
        mime_type='application/pdf',
        file_size_bytes=1234,
        status='uploaded',
        financial_year=session.financial_year,
    )
    db_session.add(new_doc)
    await db_session.commit()

    listed = await async_client.get(f'/api/workspaces/{workspace_id}/documents')
    assert listed.status_code == 200
    payload = listed.json()
    assert len(payload) == 1
    assert payload[0]['original_filename'] == 'receipt.pdf'


async def test_item_and_export_routes_require_workspace_ownership(async_client, db_session):
    workspace_id = await _setup_and_get_workspace(async_client)
    docs = await async_client.get(f'/api/workspaces/{workspace_id}/documents')
    assert docs.status_code == 200

    session_result = await db_session.execute(select(TaxSession).where(TaxSession.workspace_id == workspace_id))
    own_session = session_result.scalar_one()

    item = TaxItem(
        session_id=own_session.id,
        item_type='deduction',
        category='tools_equipment',
        amount=42.0,
        description='hammer',
        confidence=0.9,
        needs_review=True,
    )
    db_session.add(item)
    await db_session.commit()

    own_items = await async_client.get(f'/api/workspaces/{workspace_id}/items')
    assert own_items.status_code == 200
    assert len(own_items.json()) == 1

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

    other_workspace = TaxWorkspace(
        user_id=other_user.id,
        tax_year='FY2023',
        label='Other FY2023',
        status='active',
    )
    db_session.add(other_workspace)
    await db_session.flush()

    other_session = TaxSession(
        workspace_id=other_workspace.id,
        title='Other Session',
        financial_year='2022-2023',
        status='draft',
    )
    db_session.add(other_session)
    await db_session.flush()

    other_doc = Document(
        session_id=other_session.id,
        original_filename='other.pdf',
        mime_type='application/pdf',
        file_size_bytes=50,
        status='uploaded',
        financial_year='2022-2023',
    )
    db_session.add(other_doc)
    await db_session.commit()

    blocked = await async_client.get(f'/api/workspaces/{other_workspace.id}/documents')
    assert blocked.status_code == 404

    export_ok = await async_client.post(f'/api/workspaces/{workspace_id}/review-pack')
    assert export_ok.status_code == 410
