# test_frontend_routes.py
import base64
import json
import uuid
import pytest
import httpx
from backend_fastapi import app  # adjust if your module name differs

@pytest.fixture(scope="module")
def transport():
    return httpx.ASGITransport(app=app)

@pytest.mark.asyncio
async def test_front_routes_end_to_end(transport):
    state = {}

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1) Seed two small artifacts
        a1 = base64.b64encode(b"A evidence").decode()
        a2 = base64.b64encode(b"B result").decode()

        r = await ac.post("/artifacts", json={"content": a1, "mime": "text/plain", "pii_masked": False})
        assert r.status_code == 200
        dig1 = r.json()["digest"]

        r = await ac.post("/artifacts", json={"content": a2, "mime": "text/plain", "pii_masked": False})
        assert r.status_code == 200
        dig2 = r.json()["digest"]

        state["dig1"] = dig1
        state["dig2"] = dig2

        # 2) Create an incident (choose one of your mapped types)
        payload = {
            "order_id": "PO-TEST-001",
            "eta_delta_hours": 6.5,
            "problem_type": "eta_missed_machine_breakdown",  # mapped in taxonomy
            "details": {"severity": "high", "notes": "demo incident"}
        }
        r = await ac.post("/incidents", json=payload)
        assert r.status_code == 200
        incident_id = r.json()["incident_id"]
        state["incident_id"] = incident_id

        # 3) Upload two spans for that incident (so KPIs > 0 and timeline shows)
        # first span = detect, second = rca
        spans = [
            {
                "span_id": f"detect-{uuid.uuid4()}",
                "tool": "tool.call/detect-delay",
                "start_ts": 1_690_000_000,  # any increasing ints
                "end_ts":   1_690_000_500,
                "args_digest": dig1,
                "result_digest": dig1,
                "attributes": {"stage": "detect"},
                "incident_id": incident_id  # will resolve order_id on insert
            },
            {
                "span_id": f"rca-{uuid.uuid4()}",
                "tool": "llm.call/rca",
                "start_ts": 1_690_000_800,
                "end_ts":   1_690_000_900,
                "args_digest": dig2,
                "result_digest": dig2,
                "attributes": {"stage": "rca", "hypothesis": "ETA slip"},
                "incident_id": incident_id
            }
        ]
        r = await ac.post("/traces/spans", json=spans)
        assert r.status_code == 200, r.text

        # 4) Feed: should show our incident with labels/route_hints and KPIs
        r = await ac.get("/front/feed", params={"status": "open"})
        assert r.status_code == 200
        feed = r.json()
        assert isinstance(feed, list) and len(feed) >= 1

        # find our incident in the feed
        card = next((x for x in feed if x["incident_id"] == incident_id), None)
        assert card is not None
        # taxonomy fields
        assert card["type"] == "eta_missed_machine_breakdown"
        assert card["label"]  # non-empty
        assert card["route_hint"] == "/incidents/eta-missed"
        # severity meta should exist (color/priority)
        assert "severity_ui" in card and "color" in card["severity_ui"]
        # KPIs: evidence_time should be > 0
        assert card["kpis"]["evidence_time"] > 0

        # 5) Incident detail: timeline + previews + kpis
        r = await ac.get(f"/front/incident/{incident_id}")
        assert r.status_code == 200, r.text
        detail = r.json()

        assert detail["incident"]["id"] == incident_id
        assert detail["incident"]["route_hint"] == "/incidents/eta-missed"
        assert "timeline" in detail and len(detail["timeline"]) >= 2
        # check timeline structure + previews present (may be empty if pii_masked)
        for step in detail["timeline"]:
            assert "span_id" in step and "tool" in step
            assert "args_digest" in step and "result_digest" in step
            assert "args_preview" in step and "result_preview" in step

        # KPIs in detail as well
        assert detail["kpis"]["evidence_time"] > 0

        # 6) Search by order_id and type
        r = await ac.get("/front/search", params={"order_id": "PO-TEST-001"})
        assert r.status_code == 200
        results = r.json()
        assert any(x["incident_id"] == incident_id for x in results)

        r = await ac.get("/front/search", params={"type": "eta_missed_machine_breakdown"})
        assert r.status_code == 200
        results2 = r.json()
        assert any(x["incident_id"] == incident_id for x in results2)

        # 7) Approve (also validates approval span linkage works)
        r = await ac.post(f"/incidents/{incident_id}/approve")
        assert r.status_code == 200
        assert r.json()["status"] == "approved"

        # Optional: verify KPIs still computable after approval span insert
        r = await ac.get(f"/incidents/{incident_id}/kpis")
        assert r.status_code == 200
        k = r.json()
        assert k["evidence_time"] > 0
