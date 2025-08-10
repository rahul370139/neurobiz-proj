#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
AgentOps Option A implementation

This script demonstrates the “Agent/ML” responsibilities for the AgentOps replay
tool described in the project specification.  It ingests sample EDI 850 and
856 files alongside ERP and carrier CSVs, builds a canonical Order Model (COM)
with field‑level provenance, computes ETA deltas, raises an incident when the
delta exceeds a threshold, generates a deterministic root cause analysis (RCA)
and email drafts, applies regex‑based PII redaction to outbound messages,
computes content‑addressed artefact digests (SHA‑256) and emits a sequence of
spans with argument/result hashes.  All outputs are deterministic when run
against the same input data.

The script is intentionally self contained and uses only the Python standard
library.  It can be extended or integrated with a backend service once
available.

Usage:
    python agent_ops_optionA.py

Outputs:
    On completion the script prints the COM JSON, RCA JSON and span
    definitions to stdout.  It also persists artefact files into the
    `artifacts/` directory alongside this script.
"""

import csv
import datetime
import hashlib
import json
import os
import random
import re
import string
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Tuple, Optional

# -----------------------------------------------------------------------------
# Utility functions
# -----------------------------------------------------------------------------

def sha256_digest(data: bytes) -> str:
    """Return the hex encoded SHA‑256 digest of the provided bytes."""
    h = hashlib.sha256()
    h.update(data)
    return h.hexdigest()


def sha256_digest_json(obj: Any) -> Tuple[str, bytes]:
    """Serialise a Python object to JSON (with sorted keys) and return the
    digest and the encoded bytes."""
    encoded = json.dumps(obj, sort_keys=True, ensure_ascii=False).encode("utf‑8")
    return sha256_digest(encoded), encoded


def read_edi_file(path: Path) -> List[List[str]]:
    """Parse a simple EDI file into a list of segments.

    Each line is split on '*' characters into a list of elements.  Empty
    elements are represented as empty strings.  The first element of each
    segment (index 0) is the segment identifier (e.g. 'BEG', 'DTM').

    Args:
        path: Path to the EDI file.

    Returns:
        A list of segments, where each segment is itself a list of strings.
    """
    segments: List[List[str]] = []
    with path.open("r", encoding="utf‑8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("ISA") or line.startswith("GS") or line.startswith("GE") or line.startswith("IEA"):
                # Skip envelope segments for this simple parser
                continue
            # Split on '*' and strip trailing '~' if present
            if line.endswith("~"):
                line = line[:-1]
            parts = line.split("*")
            segments.append(parts)
    return segments


def parse_erp_csv(path: Path) -> Dict[str, Dict[str, str]]:
    """Load an ERP CSV keyed by order_id.

    Args:
        path: Path to the ERP CSV file.

    Returns:
        A mapping from order_id to dict of field names to values.
    """
    data: Dict[str, Dict[str, str]] = {}
    with path.open("r", encoding="utf‑8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            order_id = row["order_id"].strip()
            data[order_id] = {k: v.strip() for k, v in row.items()}
    return data


def parse_carrier_csv(path: Path) -> Dict[str, str]:
    """Load a carrier CSV keyed by order_id.

    Args:
        path: Path to the carrier CSV file.

    Returns:
        A mapping from order_id to carrier ETA ISO string.
    """
    data: Dict[str, str] = {}
    with path.open("r", encoding="utf‑8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            order_id = row["order_id"].strip()
            data[order_id] = row["carrier_eta"].strip()
    return data


def parse_datetime(dt_str: str, tm_str: Optional[str] = None) -> datetime.datetime:
    """Parse a date (YYYYMMDD) and optional time (HHMM) to a datetime.

    If tm_str is None, dt_str is interpreted as ISO 8601 date or datetime.
    If only a date is provided (YYYY-MM-DD), the time defaults to 00:00.

    Returns a naive datetime in UTC for determinism.
    """
    if tm_str is not None:
        # dt_str expected as YYYYMMDD, tm_str as HHMM
        return datetime.datetime.strptime(dt_str + tm_str, "%Y%m%d%H%M")
    # Attempt to parse ISO formats
    try:
        return datetime.datetime.fromisoformat(dt_str)
    except ValueError:
        return datetime.datetime.strptime(dt_str, "%Y-%m-%d")


def mask_pii(text: str, names_to_mask: List[str]) -> str:
    """Apply basic PII redaction to a free‑form text.

    Email addresses and phone numbers are redacted, as well as known
    customer names.

    Args:
        text: The text to redact.
        names_to_mask: A list of names (case sensitive) that should be
            obfuscated in the text.

    Returns:
        The redacted text.
    """
    # Mask email addresses: show only first character of local part
    email_pattern = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
    def _mask_email(match: re.Match[str]) -> str:
        email = match.group(0)
        local, _, domain = email.partition("@")
        if not local:
            return "***@" + domain
        return local[0] + "***@" + domain

    text = email_pattern.sub(_mask_email, text)

    # Mask phone numbers: any sequence of 10 digits, possibly separated
    phone_pattern = re.compile(r"\b(\d{3}[\-\.\s]?\d{3}[\-\.\s]?\d{4})\b")
    def _mask_phone(match: re.Match[str]) -> str:
        digits = re.sub(r"\D", "", match.group(0))
        return "***-***-" + digits[-4:]

    text = phone_pattern.sub(_mask_phone, text)

    # Mask names (simple whole word replacement).  We split names into words
    # and replace any matching word with its first letter plus asterisks.
    for name in names_to_mask:
        parts = name.split()
        for part in parts:
            if not part:
                continue
            pattern = re.compile(r"\b" + re.escape(part) + r"\b")
            replacement = part[0] + "*" * (max(len(part) - 1, 0))
            text = pattern.sub(replacement, text)
    return text


def ensure_dir(path: Path) -> None:
    """Create a directory if it does not already exist."""
    if not path.exists():
        path.mkdir(parents=True, exist_ok=True)


@dataclass
class Artifact:
    """Representation of a stored artefact."""
    digest: str
    path: Path
    mime: str
    length: int
    pii_masked: bool


@dataclass
class Span:
    """Representation of a deterministic span emitted by the agent."""
    span_id: str
    parent_id: Optional[str]
    tool: str
    start_ts: int
    end_ts: int
    args_digest: str
    result_digest: str
    attributes: Dict[str, Any] = field(default_factory=dict)


class AgentOps:
    """Core class implementing the Option A agent logic."""

    def __init__(self, base_dir: Path, data_dir_name: str = "sample_data", parsed_data: Dict[str, Any] = None):
        self.base_dir = base_dir
        self.data_dir = base_dir / data_dir_name
        self.templates_dir = self.data_dir / "templates"
        self.artifact_dir = base_dir / "artifacts"
        ensure_dir(self.artifact_dir)
        # For deterministic timestamps
        self.current_ts = 0
        self.span_counter = 1
        self.spans: List[Span] = []
        self.artifacts: Dict[str, Artifact] = {}
        # Store parsed data if provided
        self.parsed_data = parsed_data

    # ---------------------------------------------------------------------
    # Artefact management
    # ---------------------------------------------------------------------

    def _store_artifact(self, content: bytes, mime: str, pii_masked: bool) -> str:
        """Store an artefact and return its digest.

        Artefacts are content‑addressed by their SHA‑256 digest.  If an
        artefact with the same digest already exists, it is not rewritten.
        """
        digest = sha256_digest(content)
        if digest not in self.artifacts:
            artefact_path = self.artifact_dir / digest
            with artefact_path.open("wb") as f:
                f.write(content)
            self.artifacts[digest] = Artifact(
                digest=digest,
                path=artefact_path,
                mime=mime,
                length=len(content),
                pii_masked=pii_masked,
            )
        return digest

    # ---------------------------------------------------------------------
    # Span management
    # ---------------------------------------------------------------------

    def _emit_span(self, parent_id: Optional[str], tool: str, args: Any, result: Any,
                   attributes: Optional[Dict[str, Any]] = None) -> Span:
        """Create and record a span with deterministic timestamps.

        Args:
            parent_id: ID of the parent span, or None for root spans.
            tool: A string identifying the tool or operation (e.g. 'tool.call').
            args: The arguments passed to the tool.  These will be
                serialised and hashed.
            result: The result returned by the tool.  These will likewise be
                serialised and hashed.
            attributes: Additional metadata to attach to the span.

        Returns:
            The constructed Span instance.
        """
        # Serialise args and result, compute digests and store as artefacts
        args_digest, args_bytes = sha256_digest_json(args)
        result_digest, result_bytes = sha256_digest_json(result)
        self._store_artifact(args_bytes, mime="application/json", pii_masked=False)
        self._store_artifact(result_bytes, mime="application/json", pii_masked=False)

        # Create span with deterministic timestamps (each span occupies one unit)
        span_id = f"span-{self.span_counter}"
        start_ts = self.current_ts
        end_ts = start_ts + 1
        self.span_counter += 1
        self.current_ts = end_ts

        span = Span(
            span_id=span_id,
            parent_id=parent_id,
            tool=tool,
            start_ts=start_ts,
            end_ts=end_ts,
            args_digest=args_digest,
            result_digest=result_digest,
            attributes=attributes or {},
        )
        self.spans.append(span)
        return span

    # ---------------------------------------------------------------------
    # Core workflow
    # ---------------------------------------------------------------------

    def run(self) -> Tuple[Dict[str, Any], Dict[str, Any], List[Span]]:
        """Execute the full Option A workflow and return results.

        Returns:
            A tuple containing the COM JSON, RCA JSON and the list of spans.
        """
        # Check if we have pre-processed data
        if self.parsed_data:
            return self._run_with_processed_data()
        
        # Original workflow for backward compatibility
        # Step 1: read raw artefacts (850, 856, ERP, carrier)
        edi850_path = self.data_dir / "edi_850.txt"
        edi856_path = self.data_dir / "edi_856.txt"
        erp_path = self.data_dir / "erp.csv"
        carrier_path = self.data_dir / "carrier.csv"

        # Read raw file contents and store as artefacts (for preview)
        for path, tool_name in [
            (edi850_path, "tool.retrieval"),
            (edi856_path, "tool.retrieval"),
            (erp_path, "tool.retrieval"),
            (carrier_path, "tool.retrieval"),
        ]:
            with path.open("rb") as f:
                raw_bytes = f.read()
            args = {"file_path": str(path)}
            result = {"file_digest": sha256_digest(raw_bytes), "length": len(raw_bytes)}
            # Store raw artefact for result preview
            self._store_artifact(raw_bytes, mime="text/plain", pii_masked=False)
            self._emit_span(parent_id=None, tool=tool_name, args=args, result=result,
                            attributes={"file": path.name})

        # Step 2: parse EDI files and CSVs
        edi850_segments = read_edi_file(edi850_path)
        edi856_segments = read_edi_file(edi856_path)
        erp_data = parse_erp_csv(erp_path)
        carrier_data = parse_carrier_csv(carrier_path)
        # Emit a span for parsing
        parse_args = {
            "850_file": str(edi850_path),
            "856_file": str(edi856_path),
        }
        # Build COM JSON
        com_json = self._build_com_json(edi850_segments, edi856_segments, erp_data, carrier_data)
        self._emit_span(parent_id=None, tool="tool.call/parse", args=parse_args, result=com_json,
                        attributes={"operation": "build_com"})

        # Step 3: compute ETA delta and detect incident
        order_id = com_json["order_id"]["value"]
        eta_delta_hours = self._compute_eta_delta_hours(com_json)
        incident_json = None
        if eta_delta_hours is not None and eta_delta_hours > 0:
            incident_json = self._create_incident_card(order_id, eta_delta_hours)
        else:
            incident_json = {
                "order_id": order_id,
                "eta_delta_hours": eta_delta_hours,
                "status": "no_incident",
            }
        self._emit_span(parent_id=None, tool="tool.call/detect", args=com_json, result=incident_json,
                        attributes={"operation": "detect_incident"})

        # Step 4: generate RCA JSON and drafts
        rca_json = self._generate_rca_json(order_id, eta_delta_hours)
        self._emit_span(parent_id=None, tool="llm.call/rca", args=incident_json, result=rca_json,
                        attributes={"operation": "generate_rca"})

        # Step 5: generate email drafts
        drafts = self._generate_email_drafts(order_id, com_json, eta_delta_hours)
        self._emit_span(parent_id=None, tool="llm.call/email", args=rca_json, result=drafts,
                        attributes={"operation": "generate_email_drafts"})

        # Step 6: redact PII in drafts
        redacted_drafts = {
            k: mask_pii(v, names_to_mask=[com_json["customer_name"]["value"]])
            for k, v in drafts.items()
        }
        self._emit_span(parent_id=None, tool="policy.check/redact", args=drafts, result=redacted_drafts,
                        attributes={"operation": "redact_pii"})

        # For demonstration include redacted drafts in the RCA JSON for export
        rca_json["drafts"] = redacted_drafts

        return com_json, rca_json, self.spans

    def _run_with_processed_data(self) -> Tuple[Dict[str, Any], Dict[str, Any], List[Span]]:
        """Run workflow using pre-processed data."""
        print("🔄 Using pre-processed data for analysis...")
        
        # Step 1: Store processed data as artifacts
        edi850_segments = self.parsed_data['edi_850']
        edi856_segments = self.parsed_data['edi_856']
        erp_data = self.parsed_data['erp']
        carrier_data = self.parsed_data['carrier']
        
        # Store processed data as artifacts
        for data_name, data_content in [
            ('edi_850', edi850_segments),
            ('edi_856', edi856_segments),
            ('erp', erp_data),
            ('carrier', carrier_data)
        ]:
            content_bytes = json.dumps(data_content, sort_keys=True).encode('utf-8')
            args = {"data_name": data_name}
            result = {"data_digest": sha256_digest(content_bytes), "length": len(content_bytes)}
            self._store_artifact(content_bytes, mime="application/json", pii_masked=False)
            self._emit_span(parent_id=None, tool="tool.retrieval", args=args, result=result,
                            attributes={"data_type": data_name})
        
        # Step 2: Build COM JSON
        parse_args = {"data_source": "pre_processed"}
        com_json = self._build_com_json(edi850_segments, edi856_segments, erp_data, carrier_data)
        self._emit_span(parent_id=None, tool="tool.call/parse", args=parse_args, result=com_json,
                        attributes={"operation": "build_com"})
        
        # Continue with the rest of the workflow
        return self._continue_workflow(com_json)
    
    def _run_with_file_paths(self) -> Tuple[Dict[str, Any], Dict[str, Any], List[Span]]:
        """Original workflow using file paths."""
        print("🔄 Using file paths for analysis...")
        
        # Step 1: read raw artefacts (850, 856, ERP, carrier)
        edi850_path = self.data_dir / "edi_850.txt"
        edi856_path = self.data_dir / "edi_856.txt"
        erp_path = self.data_dir / "erp.csv"
        carrier_path = self.data_dir / "carrier.csv"

        # Read raw file contents and store as artefacts (for preview)
        for path, tool_name in [
            (edi850_path, "tool.retrieval"),
            (edi856_path, "tool.retrieval"),
            (erp_path, "tool.retrieval"),
            (carrier_path, "tool.retrieval"),
        ]:
            with path.open("rb") as f:
                raw_bytes = f.read()
            args = {"file_path": str(path)}
            result = {"file_digest": sha256_digest(raw_bytes), "length": len(raw_bytes)}
            # Store raw artefact for result preview
            self._store_artifact(raw_bytes, mime="text/plain", pii_masked=False)
            self._emit_span(parent_id=None, tool=tool_name, args=args, result=result,
                            attributes={"file": path.name})

        # Step 2: parse EDI files and CSVs
        edi850_segments = read_edi_file(edi850_path)
        edi856_segments = read_edi_file(edi856_path)
        erp_data = parse_erp_csv(erp_path)
        carrier_data = parse_carrier_csv(carrier_path)
        
        # Emit a span for parsing
        parse_args = {
            "850_file": str(edi850_path),
            "856_file": str(edi856_path),
        }
        
        # Build COM JSON
        com_json = self._build_com_json(edi850_segments, edi856_segments, erp_data, carrier_data)
        self._emit_span(parent_id=None, tool="tool.call/parse", args=parse_args, result=com_json,
                        attributes={"operation": "build_com"})
        
        # Continue with the rest of the workflow
        return self._continue_workflow(com_json)
    
    def _continue_workflow(self, com_json: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any], List[Span]]:
        """Continue the workflow from COM JSON creation."""
        # Step 3: compute ETA delta and detect incident
        order_id = com_json["order_id"]["value"]
        eta_delta_hours = self._compute_eta_delta_hours(com_json)
        incident_json = None
        if eta_delta_hours is not None and eta_delta_hours > 0:
            incident_json = self._create_incident_card(order_id, eta_delta_hours)
        else:
            incident_json = {
                "order_id": order_id,
                "eta_delta_hours": eta_delta_hours,
                "status": "no_incident",
            }
        self._emit_span(parent_id=None, tool="tool.call/detect", args=com_json, result=incident_json,
                        attributes={"operation": "detect_incident"})

        # Step 4: generate RCA JSON and drafts
        rca_json = self._generate_rca_json(order_id, eta_delta_hours)
        self._emit_span(parent_id=None, tool="llm.call/rca", args=incident_json, result=rca_json,
                        attributes={"operation": "generate_rca"})

        # Step 5: generate email drafts
        drafts = self._generate_email_drafts(order_id, com_json, eta_delta_hours)
        self._emit_span(parent_id=None, tool="llm.call/email", args=incident_json, result=drafts,
                        attributes={"operation": "generate_email_drafts"})

        # Step 6: redact PII in drafts (only if drafts exist)
        if drafts.get("internal_email") or drafts.get("customer_email"):
            redacted_drafts = {
                k: mask_pii(v, names_to_mask=[com_json["customer_name"]["value"]])
                for k, v in drafts.items()
            }
            self._emit_span(parent_id=None, tool="policy.check/redact", args=drafts, result=redacted_drafts,
                            attributes={"operation": "redact_pii"})
            
            # For demonstration include redacted drafts in the RCA JSON for export
            rca_json["drafts"] = redacted_drafts
        else:
            # No drafts to redact
            self._emit_span(parent_id=None, tool="policy.check/redact", args=drafts, result={},
                            attributes={"operation": "redact_pii", "note": "no_drafts_to_redact"})
            rca_json["drafts"] = {}

        return com_json, rca_json, self.spans

    # ---------------------------------------------------------------------
    # Internal helpers
    # ---------------------------------------------------------------------

    def _build_com_json(
        self,
        edi850_segments: List[List[str]],
        edi856_segments: List[List[str]],
        erp_data: Dict[str, Dict[str, str]],
        carrier_data: Dict[str, str],
    ) -> Dict[str, Any]:
        """Construct a canonical order model (COM) with provenance.

        The COM merges information from EDI 850, EDI 856, ERP and carrier files.
        Each field contains a value and a list of provenance entries.  A
        provenance entry identifies the source system, the file digest, the
        X12 segment and element (when available) and a deterministic
        observation timestamp.  For CSV sources the provenance includes
        the column name instead of segment/element.
        """
        # Precompute raw file digests for provenance
        if self.parsed_data:
            # Use processed data digests
            edi850_digest = sha256_digest(json.dumps(edi850_segments, sort_keys=True).encode('utf-8'))
            edi856_digest = sha256_digest(json.dumps(edi856_segments, sort_keys=True).encode('utf-8'))
            erp_digest = sha256_digest(json.dumps(erp_data, sort_keys=True).encode('utf-8'))
            carrier_digest = sha256_digest(json.dumps(carrier_data, sort_keys=True).encode('utf-8'))
        else:
            # Use original file digests
            edi850_path = self.data_dir / "edi_850.txt"
            edi856_path = self.data_dir / "edi_856.txt"
            erp_path = self.data_dir / "erp.csv"
            carrier_path = self.data_dir / "carrier.csv"
            
            with edi850_path.open("rb") as f:
                edi850_digest = sha256_digest(f.read())
            with edi856_path.open("rb") as f:
                edi856_digest = sha256_digest(f.read())
            with erp_path.open("rb") as f:
                erp_digest = sha256_digest(f.read())
            with carrier_path.open("rb") as f:
                carrier_digest = sha256_digest(f.read())

        # Default observation timestamp; using fixed constant for determinism
        observed_ts = "2025-08-09T00:00:00Z"

        # Helper to add provenance entry
        def prov(source_system: str, file_digest: str, segment: str, element: str) -> Dict[str, Any]:
            return {
                "source_system": source_system,
                "file_id": file_digest,
                "x12": {"segment": segment, "element": element},
                "observed_ts": observed_ts,
            }

        def prov_csv(source_system: str, file_digest: str, column: str) -> Dict[str, Any]:
            return {
                "source_system": source_system,
                "file_id": file_digest,
                "csv": {"column": column},
                "observed_ts": observed_ts,
            }

        # Parse 850 segments to find values
        order_id = None
        expected_ship_date = None
        for seg in edi850_segments:
            tag = seg[0]
            if tag == "BEG":
                # BEG*00*SA*PO123*20250101
                if len(seg) > 3:
                    order_id = seg[3]
            elif tag == "DTM":
                # DTM*037*20250802
                if len(seg) > 2 and seg[1] == "037":
                    expected_ship_date = seg[2]

        # Parse 856 segments to find actual delivery date/time
        actual_date = None
        actual_time = None
        for seg in edi856_segments:
            tag = seg[0]
            if tag == "DTM":
                # DTM*011*20250805*1200
                if len(seg) > 2 and seg[1] == "011":
                    actual_date = seg[2]
                    if len(seg) > 3:
                        actual_time = seg[3]

        # Lookup ERP record; if not found use defaults
        erp_record = erp_data.get(order_id or "", {}) if order_id else {}
        customer_name = erp_record.get("customer_name", "")
        erp_ship_date = erp_record.get("expected_ship_date")
        erp_delivery_date = erp_record.get("expected_delivery_date")

        # Determine expected_ship_date; prefer ERP over 850 DTM
        chosen_ship_date = erp_ship_date or (expected_ship_date and parse_datetime(expected_ship_date).date().isoformat())

        # Determine actual_delivery_datetime string
        actual_dt_iso = None
        if actual_date:
            dt = parse_datetime(actual_date, actual_time)
            actual_dt_iso = dt.strftime("%Y-%m-%dT%H:%M")

        # Carrier ETA
        carrier_eta = carrier_data.get(order_id or "", None)

        com = {}
        # Compose COM fields with provenance
        if order_id:
            com["order_id"] = {
                "value": order_id,
                "provenance": [prov("edi_850", edi850_digest, "BEG", "03")],
            }
        if customer_name:
            com["customer_name"] = {
                "value": customer_name,
                "provenance": [prov_csv("erp", erp_digest, "customer_name")],
            }
        if chosen_ship_date:
            com["expected_ship_date"] = {
                "value": chosen_ship_date,
                "provenance": [],
            }
            if erp_ship_date:
                com["expected_ship_date"]["provenance"].append(prov_csv("erp", erp_digest, "expected_ship_date"))
            elif expected_ship_date:
                com["expected_ship_date"]["provenance"].append(prov("edi_850", edi850_digest, "DTM", "02"))
        if erp_delivery_date:
            com["expected_delivery_date"] = {
                "value": erp_delivery_date,
                "provenance": [prov_csv("erp", erp_digest, "expected_delivery_date")],
            }
        if actual_dt_iso:
            com["actual_delivery_datetime"] = {
                "value": actual_dt_iso,
                "provenance": [prov("edi_856", edi856_digest, "DTM", "03")],
            }
        if carrier_eta:
            com["carrier_eta"] = {
                "value": carrier_eta,
                "provenance": [prov_csv("carrier", carrier_digest, "carrier_eta")],
            }
        return com

    def _compute_eta_delta_hours(self, com_json: Dict[str, Any]) -> Optional[float]:
        """Compute the ETA delta in hours between actual and carrier ETA.

        Returns None if either timestamp is missing.
        """
        try:
            actual = com_json.get("actual_delivery_datetime", {}).get("value")
            eta = com_json.get("carrier_eta", {}).get("value")
            if not actual or not eta:
                return None
            actual_dt = datetime.datetime.fromisoformat(actual)
            eta_dt = datetime.datetime.fromisoformat(eta)
            delta = actual_dt - eta_dt
            return round(delta.total_seconds() / 3600.0, 3)
        except Exception:
            return None

    def _create_incident_card(self, order_id: str, eta_delta_hours: float) -> Dict[str, Any]:
        """Create an incident card for an order.

        Args:
            order_id: The purchase order identifier.
            eta_delta_hours: The computed ETA slip in hours.

        Returns:
            A JSON serialisable dict representing the incident.
        """
        return {
            "order_id": order_id,
            "eta_delta_hours": eta_delta_hours,
            "status": "open",
            "hypothesis": f"ETA slip {eta_delta_hours} hours",
            "impact": f"Delay of {eta_delta_hours} hours compared to carrier ETA",
        }

    def _generate_rca_json(self, order_id: str, eta_delta_hours: Optional[float]) -> Dict[str, Any]:
        """Generate a root cause analysis JSON.

        Args:
            order_id: Order identifier.
            eta_delta_hours: ETA slip in hours.

        Returns:
            A dict containing hypothesis, supporting references, confidence, impact and explanation.
        """
        delta_str = f"{eta_delta_hours}" if eta_delta_hours is not None else "unknown"
        # Deterministic random for demonstration; no variability because seed is fixed
        random.seed(42)
        confidence = round(random.uniform(0.8, 0.99), 3)
        rca = {
            "order_id": order_id,
            "hypothesis": f"ETA slip {delta_str} hours",  # simple hypothesis
            "supporting_refs": ["856:DTM:011", "carrier_eta"],
            "confidence": confidence,
            "impact": f"Delay of {delta_str} hours compared to carrier ETA",
            "why": "The actual delivery time recorded in the ASN (DTM 011) was later than the ETA provided by the carrier, indicating a delay during transportation.",
        }
        return rca

    def _generate_email_drafts(self, order_id: str, com_json: Dict[str, Any], eta_delta_hours: Optional[float]) -> Dict[str, str]:
        """Render internal and customer email drafts from templates.

        Args:
            order_id: Order ID.
            com_json: COM data used to populate templates.
            eta_delta_hours: ETA slip in hours.

        Returns:
            A dict with 'internal' and 'customer' keys mapping to email strings.
            If templates are not available, returns empty strings.
        """
        # Check if templates directory exists and contains required templates
        internal_template_path = self.templates_dir / "internal_email.txt"
        customer_template_path = self.templates_dir / "customer_email.txt"
        
        # If templates don't exist, return empty drafts
        if not internal_template_path.exists() or not customer_template_path.exists():
            print(f"⚠️ Email templates not found in {self.templates_dir}")
            print("   Continuing without email generation...")
            return {
                "internal_email": "",
                "customer_email": "",
            }
        
        try:
            # Load templates
            with internal_template_path.open("r", encoding="utf‑8") as f:
                internal_tpl = f.read()
            with customer_template_path.open("r", encoding="utf‑8") as f:
                customer_tpl = f.read()

            customer_name = com_json.get("customer_name", {}).get("value", "Customer")
            delta_str = f"{eta_delta_hours}" if eta_delta_hours is not None else "unknown"

            # Fill placeholders deterministically; no randomness here
            internal_email = internal_tpl.format(order_id=order_id, eta_delta_hours=delta_str)
            customer_email = customer_tpl.format(order_id=order_id, customer_name=customer_name, eta_delta_hours=delta_str)
            return {
                "internal_email": internal_email,
                "customer_email": customer_email,
            }
        except Exception as e:
            print(f"⚠️ Error generating email drafts: {e}")
            print("   Continuing without email generation...")
            return {
                "internal_email": "",
                "customer_email": "",
            }


