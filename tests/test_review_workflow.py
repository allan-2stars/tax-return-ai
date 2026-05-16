from sqlalchemy import select

from app.models.tax_item import TaxItem
from app.models.tax_session import TaxSession
from app.models.tax_workspace import TaxWorkspace
from app.models.document import Document
from app.models.document_item import DocumentItem
from app.models.user import User


async def _setup_workspace(async_client):
    res = await async_client.post('/api/auth/setup', json={'master_password': 'supersecure123'})
    assert res.status_code == 200
    ws = await async_client.get('/api/workspaces')
    assert ws.status_code == 200
    return ws.json()[0]['id']


async def _get_workspace_session(db_session, workspace_id: str):
    row = await db_session.execute(select(TaxSession).where(TaxSession.workspace_id == workspace_id))
    session = row.scalar_one_or_none()
    assert session is not None
    return session


async def _seed_items(db_session, session_id: str):
    items = [
        TaxItem(session_id=session_id, item_type='deduction', category='tools_equipment', amount=10, description='a', needs_review=True, review_status='needs_review'),
        TaxItem(session_id=session_id, item_type='deduction', category='tools_equipment', amount=11, description='b', needs_review=False, review_status='confirmed'),
        TaxItem(session_id=session_id, item_type='deduction', category='tools_equipment', amount=12, description='c', needs_review=False, review_status='excluded'),
        TaxItem(session_id=session_id, item_type='deduction', category='tools_equipment', amount=13, description='d', needs_review=True, review_status='tax_agent_review'),
    ]
    for i in items:
        db_session.add(i)
    await db_session.commit()
    return items


async def test_workspace_items_filter_by_review_status(async_client, db_session):
    workspace_id = await _setup_workspace(async_client)
    ensure = await async_client.get(f'/api/workspaces/{workspace_id}/items')
    assert ensure.status_code == 200
    session = await _get_workspace_session(db_session, workspace_id)
    await _seed_items(db_session, session.id)

    all_items = await async_client.get(f'/api/workspaces/{workspace_id}/items')
    assert all_items.status_code == 200
    assert len(all_items.json()) == 4

    filtered = await async_client.get(f'/api/workspaces/{workspace_id}/items?review_status=needs_review')
    assert filtered.status_code == 200
    payload = filtered.json()
    assert len(payload) == 1
    assert payload[0]['review_status'] == 'needs_review'


async def test_workspace_patch_review_status_transitions(async_client, db_session):
    workspace_id = await _setup_workspace(async_client)
    ensure = await async_client.get(f'/api/workspaces/{workspace_id}/items')
    assert ensure.status_code == 200
    session = await _get_workspace_session(db_session, workspace_id)
    items = await _seed_items(db_session, session.id)
    item_id = items[0].id

    confirmed = await async_client.patch(
        f'/api/workspaces/{workspace_id}/items/{item_id}/review-status',
        json={'review_status': 'confirmed', 'note': 'checked'},
    )
    assert confirmed.status_code == 200
    assert confirmed.json()['review_status'] == 'confirmed'
    assert confirmed.json()['needs_review'] is False

    excluded = await async_client.patch(
        f'/api/workspaces/{workspace_id}/items/{item_id}/review-status',
        json={'review_status': 'excluded'},
    )
    assert excluded.status_code == 200
    assert excluded.json()['review_status'] == 'excluded'

    agent = await async_client.patch(
        f'/api/workspaces/{workspace_id}/items/{item_id}/review-status',
        json={'review_status': 'tax_agent_review'},
    )
    assert agent.status_code == 200
    assert agent.json()['review_status'] == 'tax_agent_review'
    assert agent.json()['needs_review'] is True


async def test_wrong_workspace_cannot_change_item(async_client, db_session):
    workspace_id = await _setup_workspace(async_client)
    ensure = await async_client.get(f'/api/workspaces/{workspace_id}/items')
    assert ensure.status_code == 200
    session = await _get_workspace_session(db_session, workspace_id)
    items = await _seed_items(db_session, session.id)

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

    blocked = await async_client.patch(
        f'/api/workspaces/{other_workspace.id}/items/{items[0].id}/review-status',
        json={'review_status': 'confirmed'},
    )
    assert blocked.status_code == 404


async def test_review_summary_blocks_and_allows_export(async_client, db_session):
    workspace_id = await _setup_workspace(async_client)
    ensure = await async_client.get(f'/api/workspaces/{workspace_id}/items')
    assert ensure.status_code == 200
    session = await _get_workspace_session(db_session, workspace_id)

    db_session.add(
        TaxItem(session_id=session.id, item_type='deduction', category='tools_equipment', amount=10, description='x', needs_review=True, review_status='needs_review')
    )
    await db_session.commit()

    blocked = await async_client.get(f'/api/workspaces/{workspace_id}/review-summary')
    assert blocked.status_code == 200
    blocked_payload = blocked.json()
    assert blocked_payload['ready_for_export'] is False
    assert blocked_payload['needs_review'] == 1

    # resolve item
    item_row = await db_session.execute(select(TaxItem).where(TaxItem.session_id == session.id))
    item = item_row.scalar_one()
    item.review_status = 'confirmed'
    item.needs_review = False
    await db_session.commit()

    ready = await async_client.get(f'/api/workspaces/{workspace_id}/review-summary')
    assert ready.status_code == 200
    ready_payload = ready.json()
    assert ready_payload['ready_for_export'] is True
    assert ready_payload['confirmed'] == 1


async def test_review_summary_matches_workspace_item_list_counts(async_client, db_session):
    workspace_id = await _setup_workspace(async_client)
    ensure = await async_client.get(f'/api/workspaces/{workspace_id}/items')
    assert ensure.status_code == 200
    session = await _get_workspace_session(db_session, workspace_id)

    for item in [
        TaxItem(session_id=session.id, item_type='deduction', category='tools_equipment', amount=10, description='a', needs_review=True, review_status='needs_review'),
        TaxItem(session_id=session.id, item_type='deduction', category='tools_equipment', amount=11, description='b', needs_review=True, review_status='needs_review'),
        TaxItem(session_id=session.id, item_type='deduction', category='tools_equipment', amount=12, description='c', needs_review=False, review_status='confirmed'),
    ]:
        db_session.add(item)
    await db_session.commit()

    summary = await async_client.get(f'/api/workspaces/{workspace_id}/review-summary')
    assert summary.status_code == 200
    summary_payload = summary.json()
    assert summary_payload['needs_review'] == 2

    filtered = await async_client.get(f'/api/workspaces/{workspace_id}/items?review_status=needs_review')
    assert filtered.status_code == 200
    filtered_items = filtered.json()
    assert len(filtered_items) == 2
    assert summary_payload['needs_review'] == len(filtered_items)


async def test_manual_review_document_with_zero_items_appears_and_blocks_export(async_client, db_session):
    workspace_id = await _setup_workspace(async_client)
    ensure = await async_client.get(f'/api/workspaces/{workspace_id}/items')
    assert ensure.status_code == 200
    session = await _get_workspace_session(db_session, workspace_id)

    doc = Document(
        session_id=session.id,
        original_filename='manual-needed.pdf',
        mime_type='application/pdf',
        file_size_bytes=100,
        status='needs_review',
        status_reason='Classification produced no items.',
        financial_year=session.financial_year,
    )
    db_session.add(doc)
    await db_session.commit()

    manual_docs = await async_client.get(f'/api/workspaces/{workspace_id}/manual-review-documents')
    assert manual_docs.status_code == 200
    payload = manual_docs.json()
    assert len(payload) == 1
    assert payload[0]['id'] == doc.id
    assert payload[0]['item_count'] == 0

    summary = await async_client.get(f'/api/workspaces/{workspace_id}/review-summary')
    assert summary.status_code == 200
    summary_payload = summary.json()
    assert summary_payload['manual_review_documents'] == 1
    assert summary_payload['ready_for_export'] is False
    assert any('manual review' in reason.lower() for reason in summary_payload['blocking_reasons'])


async def test_add_manual_item_links_to_document_and_resolves_manual_blocker(async_client, db_session):
    workspace_id = await _setup_workspace(async_client)
    ensure = await async_client.get(f'/api/workspaces/{workspace_id}/items')
    assert ensure.status_code == 200
    session = await _get_workspace_session(db_session, workspace_id)

    doc = Document(
        session_id=session.id,
        original_filename='manual-item-source.pdf',
        mime_type='application/pdf',
        file_size_bytes=120,
        status='needs_review',
        status_reason='No extracted items.',
        financial_year=session.financial_year,
    )
    db_session.add(doc)
    await db_session.commit()

    create_res = await async_client.post(
        f'/api/workspaces/{workspace_id}/documents/{doc.id}/manual-item',
        json={
            'description': 'User entered manual item',
            'review_status': 'needs_review',
            'item_type': 'needs_review',
            'category': 'needs_review',
        },
    )
    assert create_res.status_code == 200
    created = create_res.json()
    assert created['session_id'] == session.id
    assert created['review_status'] == 'needs_review'
    assert created['description'] == 'User entered manual item'

    links = await db_session.execute(select(DocumentItem).where(DocumentItem.document_id == doc.id))
    link = links.scalar_one_or_none()
    assert link is not None
    assert link.tax_item_id == created['id']

    manual_docs = await async_client.get(f'/api/workspaces/{workspace_id}/manual-review-documents')
    assert manual_docs.status_code == 200
    assert manual_docs.json() == []

    summary = await async_client.get(f'/api/workspaces/{workspace_id}/review-summary')
    assert summary.status_code == 200
    summary_payload = summary.json()
    assert summary_payload['manual_review_documents'] == 0
