import pytest


@pytest.mark.asyncio
async def test_bad_path_uuid_returns_normalized_validation_envelope(client):
    """A path param FastAPI itself rejects before any route runs (not a valid UUID) must come back in
    the same {code, message, details} envelope every other GxPError uses, not Starlette's raw
    {"detail": [...]} shape — the frontend's ApiError parsing (frontend/src/lib/api.ts) only reads
    code/message/details and silently falls back to a generic status text otherwise. Regression test
    for a batch_number-shaped value (e.g. "BATCH-PFS-001") landing in a batch_id path param."""
    resp = await client.get(
        "/ddcp/v1/prefilled-syringe/batches/BATCH-PFS-001/readiness",
        params={"profile_version_id": "7c4f5391-9dac-4a98-b4c7-12d0ad9fa3fc"},
    )
    assert resp.status_code == 422
    body = resp.json()
    assert body["code"] == "VALIDATION_FAILED"
    assert "batch_id" in body["message"]
    assert "valid UUID" in body["message"]
    assert body["details"]["errors"][0]["loc"] == ["path", "batch_id"]
