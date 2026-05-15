async def _setup_workspace(async_client):
    setup = await async_client.post('/api/auth/setup', json={'master_password': 'supersecure123'})
    assert setup.status_code == 200
    ws = await async_client.get('/api/workspaces')
    assert ws.status_code == 200
    return ws.json()[0]['id']


async def test_workspace_security_status_contains_plaintext_readiness(async_client):
    workspace_id = await _setup_workspace(async_client)
    res = await async_client.get(f'/api/workspaces/{workspace_id}/security/status')
    assert res.status_code == 200
    data = res.json()
    assert 'plaintext_readiness' in data
    assert 'document_pages' in data['plaintext_readiness']
    assert 'tax_items' in data['plaintext_readiness']
    assert 'classification_results' in data['plaintext_readiness']
    assert 'migration_readiness' in data


async def test_workspace_security_status_no_sensitive_values(async_client):
    workspace_id = await _setup_workspace(async_client)
    res = await async_client.get(f'/api/workspaces/{workspace_id}/security/status')
    assert res.status_code == 200
    payload = str(res.json()).lower()
    assert 'master_password' not in payload
    assert 'recovery_key_hash' not in payload
    assert 'session_token' not in payload
    assert 'encrypted_dek' not in payload
    assert 'raw_input' not in payload
    assert 'raw_output' not in payload
