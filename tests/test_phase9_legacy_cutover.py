async def test_legacy_export_route_returns_410(async_client):
    res = await async_client.get("/api/export/any-session-id")
    assert res.status_code == 410


async def test_legacy_document_route_returns_410(async_client):
    res = await async_client.get("/api/documents/?session_id=any")
    assert res.status_code == 410


async def test_legacy_item_route_returns_410(async_client):
    res = await async_client.get("/api/items/?session_id=any")
    assert res.status_code == 410


async def test_legacy_compliance_route_returns_410(async_client):
    res = await async_client.get("/api/compliance/any-session-id")
    assert res.status_code == 410
