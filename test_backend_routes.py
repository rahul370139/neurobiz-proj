import base64
import pytest
import uuid
import datetime
from httpx import AsyncClient, ASGITransport
from pathlib import Path

from backend_fastapi import app, get_supabase_client

transport = ASGITransport(app=app)

state = {}  


@pytest.fixture(scope="session", autouse=True)
def cleanup_db():
    sb = get_supabase_client()
    sb.table("spans").delete().neq("span_id", "").execute()
    sb.table("incidents").delete().neq("incident_id", "").execute()
    sb.table("artifacts").delete().neq("digest", "").execute()


@pytest.mark.asyncio
async def test_01_upload_artifacts():
    """Upload multiple realistic artifacts: JSON, CSV, PNG."""
    files = [
        (b'{"order_id": "ORD-2025-001", "status": "shipped"}', "application/json"),
        (b'product_id,qty\nSKU123,10\nSKU456,5', "text/csv"),
        (b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR', "image/png")
    ]
    digests = []
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        for content_bytes, mime in files:
            b64_content = base64.b64encode(content_bytes).decode()
            resp = await ac.post("/artifacts", json={
                "content": b64_content,
                "mime": mime,
                "pii_masked": False
            })
            assert resp.status_code == 200
            digests.append(resp.json()["digest"])
            assert (Path("artifacts") / resp.json()["digest"]).exists()
    state["digests"] = digests


@pytest.mark.asyncio
async def test_02_upload_spans():
    """Upload realistic spans referencing uploaded artifacts."""
    ts_start = int(datetime.datetime.utcnow().timestamp())
    ts_mid = ts_start + 120
    ts_end = ts_mid + 180

    spans = [
        {
            "span_id": str(uuid.uuid4()),
            "tool": "tool.call/detect-delay",
            "start_ts": ts_start,
            "end_ts": ts_mid,
            "args_digest": state["digests"][0],  # JSON
            "result_digest": state["digests"][1],  # CSV
            "attributes": {"severity": "high"}
        },
        {
            "span_id": str(uuid.uuid4()),
            "tool": "llm.call/rca",
            "start_ts": ts_mid,
            "end_ts": ts_end,
            "args_digest": state["digests"][1],  # CSV
            "result_digest": state["digests"][2],  # PNG
            "attributes": {"rca": "Port congestion due to storm"}
        }
    ]
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post("/traces/spans", json=spans)
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_03_create_incident():
    """Create an incident with realistic metadata."""
    payload = {
        "order_id": "ORD-2025-001",
        "eta_delta_hours": 8,
        "problem_type": "eta_missed",
        "details": {
            "expected_eta": "2025-08-15T10:00:00Z",
            "actual_eta": "2025-08-15T18:00:00Z",
            "reason": "Port congestion"
        }
    }
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post("/incidents", json=payload)
        assert resp.status_code == 200
        state["incident_id"] = resp.json()["incident_id"]


@pytest.mark.asyncio
async def test_04_get_incident():
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get(f"/incidents/{state['incident_id']}")
        assert resp.status_code == 200
        assert resp.json()["id"] == state["incident_id"]


@pytest.mark.asyncio
async def test_05_list_incidents_filter():
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/incidents", params={"problem_type": "eta_missed"})
        assert resp.status_code == 200
        assert any(inc["id"] == state["incident_id"] for inc in resp.json())


@pytest.mark.asyncio
async def test_06_approve_incident():
    """Insert placeholder artifact before approve to pass FK check."""
    sb = get_supabase_client()
    sb.table("artifacts").upsert({
        "digest": "0"*64,
        "mime_type": "application/octet-stream",
        "length": 0,
        "pii_masked": False,
        "file_path": f"artifacts/{'0'*64}",
        "metadata": {}
    }).execute()

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(f"/incidents/{state['incident_id']}/approve")
        assert resp.status_code == 200
        assert resp.json()["status"] == "approved"


@pytest.mark.asyncio
async def test_07_incident_kpis():
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get(f"/incidents/{state['incident_id']}/kpis")
        assert resp.status_code == 200
        data = resp.json()
        assert data["evidence_time"] > 0
        assert data["time_to_rca"] > 0


@pytest.mark.asyncio
async def test_08_replay_strict():
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post("/replay/strict", json={"incident_id": state["incident_id"]})
        assert resp.status_code == 200
        data = resp.json()
        assert "incident" in data and "outputs" in data


@pytest.mark.asyncio
async def test_09_export_bundle():
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post("/bundles", json={"incident_id": state["incident_id"]})
        assert resp.status_code == 200
        raw_bytes = base64.b64decode(resp.json()["bundle"])
        assert raw_bytes[:2] == b"PK"  # ZIP magic number


@pytest.mark.asyncio
async def test_10_problem_specific_routes():
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        payload = {
            "order_id": "ORD-2025-002",
            "eta_delta_hours": 12,
            "problem_type": "ignored",
            "details": {"machine": "M-45"}
        }
        resp = await ac.post("/incidents/eta-missed/machine-breakdown", json=payload)
        assert resp.status_code == 200
        new_id = resp.json()["incident_id"]
        resp_get = await ac.get(f"/incidents/{new_id}")
        assert resp_get.status_code == 200
        assert resp_get.json()["problem_type"] == "eta_missed_machine_breakdown"
