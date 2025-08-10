#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
FastAPI backend for AgentOps (Option B).

This module exposes REST endpoints backed by Supabase (PostgreSQL) and a local
file‑based artefact store.  It implements the core functionality required to
capture artefacts and spans, create and manage incidents, compute KPIs, perform
strict replay and export signed bundles.  It also defines separate routes
for the various supply‑chain problems discovered in the ERP domain, making it
easy to create incidents for each category.

Environment variables:
    SUPABASE_URL:  URL of your Supabase instance
    SUPABASE_KEY:  Service or anon key with database insert/update rights
    ARTIFACT_DIR:  Directory where artefact blobs are stored (default
                   ./artifacts)

Note:  This module depends on the `fastapi` and `supabase_py` packages. If
they are not installed, run `pip install fastapi supabase_py uvicorn`.
"""

import base64
import datetime
import hashlib
import json
import os
import uuid
import zipfile
from io import BytesIO
from pathlib import Path
from typing import List, Optional, Dict, Any

from fastapi import FastAPI, HTTPException, Path as PathParam, Body
from fastapi import Query
from pydantic import BaseModel, Field

try:
    from supabase import create_client  # type: ignore
except ImportError:
    create_client = None  # Will error at runtime if used without installation

SUPABASE_URL =  "https://pobjkgrokyzhpbnnylzy.supabase.co/"#os.environ.get("SUPABASE_URL")
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InBvYmprZ3Jva3l6aHBibm55bHp5Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTQ3ODE2MDUsImV4cCI6MjA3MDM1NzYwNX0.9xSjIeHw5Onudc-UfbVEtYJefPZ6wto-l3ESvBkUdi8"#os.environ.get("SUPABASE_KEY")
ARTIFACT_DIR = Path(os.environ.get("ARTIFACT_DIR", "artifacts"))
INCIDENT_TAXONOMY = {
    "master_data_wrong_product": {"route": "/incidents/master-data", "label": "Master Data – Product Mismatch", "bucket": "master_data", "suggested_actions": ["Fix mapping", "Notify supplier", "Add preventive rule"]},
    "master_data_uom_mismatch": {"route": "/incidents/master-data", "label": "Master Data – UOM Mismatch", "bucket": "master_data", "suggested_actions": ["Normalize UOM", "Update UOM table"]},
    "eta_missed": {"route": "/incidents/eta-missed", "label": "ETA Missed", "bucket": "eta", "suggested_actions": ["Replan shipment", "Notify customer", "Expedite leg"]},
    "eta_missed_component_unavailable": {"route": "/incidents/eta-missed", "label": "ETA Missed – Component Shortage", "bucket": "eta", "suggested_actions": ["Reallocate stock", "Supplier expedite"]},
    "eta_missed_machine_breakdown": {"route": "/incidents/eta-missed", "label": "ETA Missed – Machine Breakdown", "bucket": "eta", "suggested_actions": ["Maintenance ticket", "Predictive maintenance"]},
    "eta_missed_shipping_method_unavailable": {"route": "/incidents/eta-missed", "label": "ETA Missed – Shipping Method Unavailable", "bucket": "eta", "suggested_actions": ["Switch carrier", "Mode change"]},
    "weather_issue": {"route": "/incidents/weather", "label": "Weather Delay", "bucket": "external", "suggested_actions": ["Reroute", "Customer notify"]},
    "payment_delay_system": {"route": "/incidents/payment", "label": "Payment – System Issue", "bucket": "payment", "suggested_actions": ["Unblock gateway", "Retry payment"]},
    "payment_delay_customer_late": {"route": "/incidents/payment", "label": "Payment – Customer Late", "bucket": "payment", "suggested_actions": ["Reminder email", "Credit terms review"]},
    "payment_delay_credit_block": {"route": "/incidents/payment", "label": "Payment – Credit Block", "bucket": "payment", "suggested_actions": ["Credit review", "Partial release"]},
    "out_of_stock": {"route": "/incidents/stock", "label": "Out of Stock", "bucket": "stock", "suggested_actions": ["Partial ship", "Backorder plan"]},
    "out_of_stock_customer_no_permission": {"route": "/incidents/stock", "label": "Partial Shipment Not Allowed", "bucket": "stock", "suggested_actions": ["Get approval", "Reconfirm split"]},
    "out_of_stock_deliverer_waiting": {"route": "/incidents/stock", "label": "Deliverer Waiting for Advice", "bucket": "stock", "suggested_actions": ["Contact consignee", "Escalate logistics"]},
    "transporter_delay": {"route": "/incidents/transport", "label": "Transporter Delay", "bucket": "transport", "suggested_actions": ["SLA claim", "Backup carrier"]},
    "transporter_delay_no_refrigerated_truck": {"route": "/incidents/transport", "label": "Transporter – No Refrigerated Truck", "bucket": "transport", "suggested_actions": ["Reschedule reefer", "Alternate carrier"]},
    "erp_down": {"route": "/incidents/system", "label": "ERP Down / Hacked", "bucket": "system", "suggested_actions": ["IT incident", "Failover runbook"]},
}
SEVERITY_META = {
    "low": {"color": "green", "priority": 1},
    "medium": {"color": "amber", "priority": 2},
    "high": {"color": "orange", "priority": 3},
    "critical": {"color": "red", "priority": 4},
}
def _tax(i_type: str):
    return INCIDENT_TAXONOMY.get(i_type, {"route": "/incidents/other", "label": i_type, "bucket": "other", "suggested_actions": []})
def _sev_meta(sev: str):
    return SEVERITY_META.get(sev or "low", {"color": "gray", "priority": 0})
def sha256_digest(data: bytes) -> str:
    h = hashlib.sha256()
    h.update(data)
    return h.hexdigest()

EMPTY_DIGEST = sha256_digest(b"")

app = FastAPI(title="AgentOps Backend", version="1.0.0")


def get_supabase_client():
    if not create_client:
        raise RuntimeError(
            "supabase_py is not installed. Install it with `pip install supabase_py`."
        )
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise RuntimeError(
            "SUPABASE_URL and SUPABASE_KEY environment variables must be set."
        )
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def sha256_digest(data: bytes) -> str:
    h = hashlib.sha256()
    h.update(data)
    return h.hexdigest()


# ---------------------------- Pydantic models ------------------------------

class ArtifactIn(BaseModel):
    content: str = Field(..., description="Base64 encoded artifact content")
    mime: str = Field("application/octet-stream", description="MIME type")
    pii_masked: bool = Field(False, description="Whether PII has been masked")


class ArtifactOut(BaseModel):
    digest: str
    mime: str
    preview: str
    length: int
    pii_masked: bool


class SpanIn(BaseModel):
    span_id: str
    parent_id: Optional[str] = None
    tool: str
    start_ts: int
    end_ts: int
    args_digest: str
    result_digest: str
    attributes: Dict[str, Any] = Field(default_factory=dict)
    incident_id: Optional[str] = None
    order_id: Optional[str] = None

class IncidentsCreate(BaseModel):
    order_id: str
    eta_delta_hours: float
    problem_type: str
    details: Dict[str, Any] = Field(default_factory=dict)


class IncidentOut(BaseModel):
    id: str
    order_id: str
    eta_delta_hours: float
    problem_type: str
    status: str
    created_ts: str
    details: Dict[str, Any]


class KPIsOut(BaseModel):
    evidence_time: float
    time_to_rca: float
    tokens_cost: float


class BundleOut(BaseModel):
    bundle: str


# --------------------------- Helper functions -----------------------------

async def store_artifact_in_db(sb, digest: str, mime: str, length: int, pii_masked: bool) -> None:
    # Upsert into Supabase artifacts table
    sb.table("artifacts").upsert(
        {
            "digest": digest,
            "mime_type": mime,
            "length": length,
            "pii_masked": pii_masked,
            "created_at": datetime.datetime.utcnow().isoformat(),
            "file_path": f"artifacts/{digest}",
            "metadata": {},
        },
        on_conflict="digest",
    ).execute()


async def get_artifact_from_db(sb, digest: str) -> Optional[dict]:
    response = sb.table("artifacts").select("*").eq("digest", digest).single().execute()
    data = response.data
    if data:
        # Map the database schema to the expected format
        return {
            "digest": data["digest"],
            "mime": data["mime_type"],
            "length": data["length"],
            "pii_masked": data["pii_masked"],
            "created_ts": data["created_at"],
        }
    return None


async def store_span_in_db(sb, span: SpanIn) -> None:
    resolved_order_id = span.order_id
    if not resolved_order_id and span.incident_id:
        r = sb.table("incidents").select("order_id").eq("incident_id", span.incident_id).single().execute()
        if r.data:
            resolved_order_id = r.data["order_id"]
    if not resolved_order_id:
        raise HTTPException(status_code=400, detail="span must include order_id or incident_id that maps to an order_id")

    span_data = {
        "span_id": span.span_id,
        "parent_id": span.parent_id,
        "tool": span.tool,
        "start_ts": span.start_ts,
        "end_ts": span.end_ts,
        "args_digest": span.args_digest,
        "result_digest": span.result_digest,
        "attributes": span.attributes,
        "created_at": datetime.datetime.utcnow().isoformat(),
        "order_id": resolved_order_id,
    }
    sb.table("spans").insert(span_data).execute()



async def create_incident_in_db(sb, payload: IncidentsCreate) -> str:
    incident_id = str(uuid.uuid4())
    record = {
        "incident_id": incident_id,
        "order_id": payload.order_id,
        "incident_type": payload.problem_type,
        "severity": "medium",  # Default severity
        "status": "open",
        "eta_delta_hours": payload.eta_delta_hours,
        "description": json.dumps(payload.details),
        "created_at": datetime.datetime.utcnow().isoformat(),
        "metadata": payload.details,
    }
    sb.table("incidents").insert(record).execute()
    return incident_id


async def list_incidents_from_db(sb, problem_type: Optional[str]) -> List[IncidentOut]:
    query = sb.table("incidents").select("*")
    if problem_type:
        query = query.eq("incident_type", problem_type)
    resp = query.execute()
    rows = resp.data or []
    return [
        IncidentOut(
            id=row["incident_id"],
            order_id=row["order_id"],
            eta_delta_hours=row["eta_delta_hours"],
            problem_type=row["incident_type"],
            status=row["status"],
            created_ts=row["created_at"],
            details=row["metadata"] or {},
        )
        for row in rows
    ]


async def get_incident_from_db(sb, incident_id: str) -> Optional[IncidentOut]:
    resp = sb.table("incidents").select("*").eq("incident_id", incident_id).single().execute()
    row = resp.data
    if not row:
        return None
    return IncidentOut(
        id=row["incident_id"],
        order_id=row["order_id"],
        eta_delta_hours=row["eta_delta_hours"],
        problem_type=row["incident_type"],
        status=row["status"],
        created_ts=row["created_at"],
        details=row["metadata"] or {},
    )


async def approve_incident_in_db(sb, incident_id: str) -> None:
    sb.table("incidents").update({"status": "resolved"}).eq("incident_id", incident_id).execute()


async def list_spans_for_incident(sb, incident_id: str) -> List[dict]:
    # Get the order_id from the incident first
    incident_resp = sb.table("incidents").select("order_id").eq("incident_id", incident_id).single().execute()
    if not incident_resp.data:
        return []
    
    order_id = incident_resp.data["order_id"]
    resp = sb.table("spans").select("*").eq("order_id", order_id).execute()
    return resp.data or []


def compute_kpis_from_spans(spans: List[dict]) -> KPIsOut:
    if not spans:
        return KPIsOut(evidence_time=0, time_to_rca=0, tokens_cost=0)
    start_times = [s["start_ts"] for s in spans]
    end_times = [s["end_ts"] for s in spans]
    evidence_time = float(max(end_times) - min(start_times))
    detect_ts = None
    rca_ts = None
    for s in spans:
        tool = s["tool"]
        if tool.startswith("tool.call/detect") and detect_ts is None:
            detect_ts = s["start_ts"]
        if tool.startswith("llm.call/rca") and rca_ts is None:
            rca_ts = s["start_ts"]
    time_to_rca = float(rca_ts - detect_ts) if detect_ts is not None and rca_ts is not None else 0
    return KPIsOut(evidence_time=evidence_time, time_to_rca=time_to_rca, tokens_cost=0)


def build_bundle_bytes(incident: IncidentOut, spans: List[dict]) -> bytes:
    manifest = {
        "incident": incident.dict(),
        "spans": spans,
        "generated_at": datetime.datetime.utcnow().isoformat(),
    }
    manifest_bytes = json.dumps(manifest, sort_keys=True, ensure_ascii=False).encode("utf-8")
    manifest_digest = sha256_digest(manifest_bytes)
    # Collect unique artefact digests
    artefact_digests = set()
    for span in spans:
        artefact_digests.add(span["args_digest"])
        artefact_digests.add(span["result_digest"])
    # Build zip
    buf = BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("manifest.json", manifest_bytes)
        # Add artifacts
        for digest in artefact_digests:
            art_path = ARTIFACT_DIR / digest
            if art_path.exists():
                with art_path.open("rb") as f:
                    zf.writestr(f"artifacts/{digest}", f.read())
        checksums = {
            "manifest": manifest_digest,
            "artifacts": sorted(list(artefact_digests)),
        }
        checksums_bytes = json.dumps(checksums, sort_keys=True).encode("utf-8")
        zf.writestr("checksums.json", checksums_bytes)
        # Dummy signature
        secret = b"agentops-private-key"
        signature = sha256_digest(manifest_bytes + checksums_bytes + secret).encode("utf-8")
        zf.writestr("signatures/key.sig", signature)
    return buf.getvalue()


async def strict_replay_data(sb, incident_id: str) -> Dict[str, Any]:
    incident = await get_incident_from_db(sb, incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    spans = await list_spans_for_incident(sb, incident_id)
    outputs = []
    for span in sorted(spans, key=lambda s: s["start_ts"]):
        digest = span["result_digest"]
        art = await get_artifact_from_db(sb, digest)
        # Read preview from local FS
        preview = ""
        art_path = ARTIFACT_DIR / digest
        if art_path.exists():
            with art_path.open("rb") as f:
                preview_bytes = f.read(256)
                preview = base64.b64encode(preview_bytes).decode("ascii")
        outputs.append({"tool": span["tool"], "result_digest": digest, "preview": preview})
    return {"incident": incident.dict(), "outputs": outputs}


# ------------------------------ API routes -------------------------------
# EMPTY_DIGEST = sha256_digest(b"")
@app.on_event("startup")
async def startup_event() -> None:
    # Ensure artifact directory exists
    ARTIFACT_DIR.mkdir(exist_ok=True)

    # Ensure the empty artifact exists both on disk and in DB (for approval spans)
    try:
        sb = get_supabase_client()
    except Exception:
        # If supabase isn’t configured in some environments, just return
        return

    empty_path = ARTIFACT_DIR / EMPTY_DIGEST
    if not empty_path.exists():
        empty_path.write_bytes(b"")

    # Upsert metadata row so FK on spans(args_digest/result_digest) is satisfied
    await store_artifact_in_db(
        sb,
        digest=EMPTY_DIGEST,
        mime="application/octet-stream",
        length=0,
        pii_masked=False,
    )


@app.post("/artifacts", response_model=Dict[str, str])
async def upload_artifact(payload: ArtifactIn):
    sb = get_supabase_client()
    content = base64.b64decode(payload.content)
    digest = sha256_digest(content)
    # Save file locally
    path = ARTIFACT_DIR / digest
    if not path.exists():
        with path.open("wb") as f:
            f.write(content)
    # Upsert metadata into Supabase
    await store_artifact_in_db(sb, digest, payload.mime, len(content), payload.pii_masked)
    return {"digest": digest}


@app.get("/artifacts/{digest}", response_model=ArtifactOut)
async def get_artifact(digest: str = PathParam(...)):
    sb = get_supabase_client()
    art = await get_artifact_from_db(sb, digest)
    if not art:
        raise HTTPException(status_code=404, detail="Artifact not found")
    # Read preview from local file
    preview_bytes = b""
    path = ARTIFACT_DIR / digest
    if path.exists():
        with path.open("rb") as f:
            preview_bytes = f.read(256)
    preview_b64 = base64.b64encode(preview_bytes).decode("ascii")
    return ArtifactOut(
        digest=digest,
        mime=art["mime"],
        preview=preview_b64,
        length=art["length"],
        pii_masked=bool(art["pii_masked"]),
    )


@app.post("/traces/spans")
async def upload_spans(spans: List[SpanIn]):
    sb = get_supabase_client()
    # Validate digests exist
    for span in spans:
        art_args = await get_artifact_from_db(sb, span.args_digest)
        art_result = await get_artifact_from_db(sb, span.result_digest)
        if art_args is None:
            raise HTTPException(status_code=400, detail=f"Unknown args_digest {span.args_digest}")
        if art_result is None:
            raise HTTPException(status_code=400, detail=f"Unknown result_digest {span.result_digest}")
    # Insert spans
    for span in spans:
        await store_span_in_db(sb, span)
    return {"status": "ok"}


@app.post("/incidents", response_model=Dict[str, str])
async def create_incident(payload: IncidentsCreate):
    sb = get_supabase_client()
    incident_id = await create_incident_in_db(sb, payload)
    return {"incident_id": incident_id}


@app.get("/incidents", response_model=List[IncidentOut])
async def list_incidents(problem_type: Optional[str] = None):
    sb = get_supabase_client()
    return await list_incidents_from_db(sb, problem_type)


@app.get("/incidents/{incident_id}", response_model=IncidentOut)
async def get_incident(incident_id: str = PathParam(...)):
    sb = get_supabase_client()
    incident = await get_incident_from_db(sb, incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident


@app.post("/incidents/{incident_id}/approve")
async def approve_incident(incident_id: str = PathParam(...)):
    sb = get_supabase_client()
    await approve_incident_in_db(sb, incident_id)

    r = sb.table("incidents").select("order_id").eq("incident_id", incident_id).single().execute()
    if not r.data:
        raise HTTPException(status_code=404, detail="Incident not found")
    order_id = r.data["order_id"]
    empty_path = ARTIFACT_DIR / EMPTY_DIGEST
    if not empty_path.exists():
        empty_path.write_bytes(b"")
    await store_artifact_in_db(
        sb,
        digest=EMPTY_DIGEST,
        mime="application/octet-stream",
        length=0,
        pii_masked=False,
    )
    now = int(datetime.datetime.utcnow().timestamp())
    span_id = str(uuid.uuid4())
    span_data = {
        "span_id": span_id,
        "parent_id": None,
        "tool": "human.approval",
        "start_ts": now,
        "end_ts": now + 1,
        "args_digest": EMPTY_DIGEST,
        "result_digest": EMPTY_DIGEST,
        "attributes": {"incident_id": incident_id, "action": "approve"},
        "created_at": datetime.datetime.utcnow().isoformat(),
        "order_id": order_id,
    }
    sb.table("spans").insert(span_data).execute()
    return {"status": "approved"}


@app.get("/incidents/{incident_id}/kpis", response_model=KPIsOut)
async def incident_kpis(incident_id: str = PathParam(...)):
    sb = get_supabase_client()
    spans = await list_spans_for_incident(sb, incident_id)
    return compute_kpis_from_spans(spans)


@app.post("/replay/strict")
async def replay_strict(body: Dict[str, str] = Body(...)):
    sb = get_supabase_client()
    incident_id = body.get("incident_id")
    if not incident_id:
        raise HTTPException(status_code=400, detail="incident_id required")
    return await strict_replay_data(sb, incident_id)


@app.post("/bundles", response_model=BundleOut)
async def export_bundle(body: Dict[str, str] = Body(...)):
    sb = get_supabase_client()
    incident_id = body.get("incident_id")
    if not incident_id:
        raise HTTPException(status_code=400, detail="incident_id required")
    incident = await get_incident_from_db(sb, incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    spans = await list_spans_for_incident(sb, incident_id)
    bundle_bytes = build_bundle_bytes(incident, spans)
    bundle_b64 = base64.b64encode(bundle_bytes).decode("ascii")
    return BundleOut(bundle=bundle_b64)


# ---------------- Problem-specific incident routes ------------------------

def register_problem_route(route: str, problem_type: str):
    @app.post(route)
    async def create_specific_incident(payload: IncidentsCreate):  # type: ignore
        # Override problem_type
        payload.problem_type = problem_type
        sb = get_supabase_client()
        incident_id = await create_incident_in_db(sb, payload)
        return {"incident_id": incident_id}
    return create_specific_incident

@app.get("/front/feed")
async def front_feed(
    status: Optional[str] = Query(None),
    incident_type: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    order_id: Optional[str] = Query(None),
    limit: int = 50,
    offset: int = 0,
):
    sb = get_supabase_client()
    q = sb.table("incidents").select("*").order("created_at", desc=True)
    if status:        q = q.eq("status", status)
    if incident_type: q = q.eq("incident_type", incident_type)
    if severity:      q = q.eq("severity", severity)
    if order_id:      q = q.eq("order_id", order_id)
    q = q.range(offset, offset + limit - 1)
    resp = q.execute()
    rows = resp.data or []

    out = []
    for r in rows:
        spans = await list_spans_for_incident(sb, r["incident_id"])
        kpis = compute_kpis_from_spans(spans)
        tax = _tax(r["incident_type"])
        out.append({
            "incident_id": r["incident_id"],
            "order_id": r["order_id"],
            "type": r["incident_type"],
            "label": tax["label"],
            "route_hint": tax["route"],
            "bucket": tax["bucket"],
            "severity": r["severity"],
            "severity_ui": _sev_meta(r["severity"]),
            "status": r["status"],
            "eta_delta_hours": r.get("eta_delta_hours"),
            "created_at": r["created_at"],
            "kpis": kpis.dict(),
            "suggested_actions": tax["suggested_actions"],
        })
    return out

@app.get("/front/incident/{incident_id}")
async def front_incident_detail(incident_id: str):
    sb = get_supabase_client()
    inc = await get_incident_from_db(sb, incident_id)
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found")

    spans = await list_spans_for_incident(sb, incident_id)
    spans_sorted = sorted(spans, key=lambda s: (s["start_ts"], s["end_ts"]))

    # previews for arg/result (first 256 bytes; blank if pii_masked)
    preview_map: Dict[str, str] = {}
    digests = set()
    for s in spans_sorted:
        if s["args_digest"]:   digests.add(s["args_digest"])
        if s["result_digest"]: digests.add(s["result_digest"])
    for d in digests:
        art = await get_artifact_from_db(sb, d)
        if not art:
            continue
        p64 = ""
        p = ARTIFACT_DIR / d
        if p.exists():
            with p.open("rb") as f:
                p64 = base64.b64encode(f.read(256)).decode("ascii")
        preview_map[d] = "" if bool(art.get("pii_masked")) else p64

    timeline = [{
        "span_id": s["span_id"],
        "tool": s["tool"],
        "start_ts": s["start_ts"],
        "end_ts": s["end_ts"],
        "attributes": s.get("attributes") or {},
        "args_digest": s["args_digest"],
        "result_digest": s["result_digest"],
        "args_preview": preview_map.get(s["args_digest"], ""),
        "result_preview": preview_map.get(s["result_digest"], ""),
    } for s in spans_sorted]

    tax = _tax(inc.problem_type)
    kpis = compute_kpis_from_spans(spans)

    # If you saved these during your RCA step
    reasoning_digest = (inc.details or {}).get("reasoning_digest")
    email_digest = (inc.details or {}).get("email_digest")
    note_digest  = (inc.details or {}).get("note_digest")

    return {
        "incident": {
            "id": inc.id,
            "order_id": inc.order_id,
            "type": inc.problem_type,
            "label": tax["label"],
            "route_hint": tax["route"],
            "bucket": tax["bucket"],
            "severity": (inc.details or {}).get("severity", "medium"),  # switch to inc.severity if you want
            "status": inc.status,
            "eta_delta_hours": inc.eta_delta_hours,
            "created_at": inc.created_ts,
            "suggested_actions": tax["suggested_actions"],
        },
        "kpis": kpis.dict(),
        "timeline": timeline,
        "reasoning_digest": reasoning_digest,
        "email_digest": email_digest,
        "note_digest": note_digest,
    }

@app.get("/front/search")
async def front_search(
    q: Optional[str] = None,
    order_id: Optional[str] = None,
    type: Optional[str] = None,
    status: Optional[str] = None,
    severity: Optional[str] = None,
    carrier: Optional[str] = None,  # requires carrier stored in incidents.metadata
    limit: int = 50
):
    sb = get_supabase_client()
    qy = sb.table("incidents").select("*").order("created_at", desc=True).limit(limit)
    if order_id: qy = qy.eq("order_id", order_id)
    if type:     qy = qy.eq("incident_type", type)
    if status:   qy = qy.eq("status", status)
    if severity: qy = qy.eq("severity", severity)
    if carrier:  qy = qy.contains("metadata", {"carrier": carrier})
    if q:        qy = qy.ilike("description", f"%{q}%")
    resp = qy.execute()
    rows = resp.data or []

    out = []
    for r in rows:
        tax = _tax(r["incident_type"])
        out.append({
            "incident_id": r["incident_id"],
            "order_id": r["order_id"],
            "type": r["incident_type"],
            "label": tax["label"],
            "route_hint": tax["route"],
            "severity": r["severity"],
            "status": r["status"],
            "created_at": r["created_at"],
        })
    return out


# Register routes for each problem category
register_problem_route("/incidents/master-data/wrong-product", "master_data_wrong_product")
register_problem_route("/incidents/master-data/uom-mismatch", "master_data_uom_mismatch")
register_problem_route("/incidents/eta-missed", "eta_missed")
register_problem_route("/incidents/eta-missed/component-unavailable", "eta_missed_component_unavailable")
register_problem_route("/incidents/eta-missed/machine-breakdown", "eta_missed_machine_breakdown")
register_problem_route("/incidents/eta-missed/shipping-method-unavailable", "eta_missed_shipping_method_unavailable")
register_problem_route("/incidents/weather-issue", "weather_issue")
register_problem_route("/incidents/payment-delay/payment-system", "payment_delay_system")
register_problem_route("/incidents/payment-delay/customer-late", "payment_delay_customer_late")
register_problem_route("/incidents/payment-delay/credit-block", "payment_delay_credit_block")
register_problem_route("/incidents/out-of-stock", "out_of_stock")
register_problem_route("/incidents/out-of-stock/customer-no-permission", "out_of_stock_customer_no_permission")
register_problem_route("/incidents/out-of-stock/deliverer-waiting", "out_of_stock_deliverer_waiting")
register_problem_route("/incidents/transporter-delay", "transporter_delay")
register_problem_route("/incidents/transporter-delay/no-refrigerated-truck", "transporter_delay_no_refrigerated_truck")
register_problem_route("/incidents/erp-down", "erp_down")