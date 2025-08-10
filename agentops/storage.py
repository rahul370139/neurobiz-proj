#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
AgentOps Backend System

This backend handles artifact persistence, span storage, and incident management.
It provides a clean interface for storing artifacts, traces, and incidents in Supabase.
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
import hashlib
import mimetypes
import sys

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # Continue without dotenv if not available

# Supabase integration
try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    print("Error: Supabase client required. Install with: pip install supabase")
    sys.exit(1)

# -----------------------------------------------------------------------------
# Data Models
# -----------------------------------------------------------------------------

@dataclass
class ArtifactRecord:
    """Database record for an artifact."""
    digest: str
    mime_type: str
    length: int
    pii_masked: bool
    created_at: str
    file_path: str
    metadata: Dict[str, Any]

@dataclass
class SpanRecord:
    """Database record for a span."""
    span_id: str
    parent_id: Optional[str]
    tool: str
    start_ts: int
    end_ts: int
    args_digest: str
    result_digest: str
    attributes: Dict[str, Any]
    created_at: str
    order_id: str  # Link spans to orders

@dataclass
class IncidentRecord:
    """Database record for an incident."""
    incident_id: str
    order_id: str
    incident_type: str
    severity: str
    status: str
    eta_delta_hours: Optional[float]
    description: str
    created_at: str
    resolved_at: Optional[str]
    metadata: Dict[str, Any]

# -----------------------------------------------------------------------------
# Supabase Database Interface
# -----------------------------------------------------------------------------

class SupabaseDatabase:
    """Supabase implementation for artifact and span storage."""
    
    def __init__(self, url: str, key: str):
        if not SUPABASE_AVAILABLE:
            raise ImportError("Supabase client not available")
        
        self.client: Client = create_client(url, key)
    
    def store_artifact(self, artifact: ArtifactRecord) -> bool:
        """Store an artifact record in Supabase."""
        try:
            data = asdict(artifact)
            data['metadata'] = json.dumps(data['metadata'])
            
            result = self.client.table('artifacts').upsert(data).execute()
            if len(result.data) > 0:
                print(f"  ✅ Artifact stored in Supabase: {artifact.digest}")
                return True
            else:
                print(f"  ❌ No data returned from Supabase for artifact: {artifact.digest}")
                return False
        except Exception as e:
            print(f"  ❌ Error storing artifact {artifact.digest} in Supabase: {e}")
            return False
    
    def store_span(self, span: SpanRecord) -> bool:
        """Store a span record in Supabase."""
        try:
            data = asdict(span)
            data['attributes'] = json.dumps(data['attributes'])
            
            result = self.client.table('spans').upsert(data).execute()
            if len(result.data) > 0:
                print(f"  ✅ Span stored in Supabase: {span.span_id}")
                return True
            else:
                print(f"  ❌ No data returned from Supabase for span: {span.span_id}")
                return False
        except Exception as e:
            print(f"  ❌ Error storing span {span.span_id} in Supabase: {e}")
            return False
    
    def store_incident(self, incident: IncidentRecord) -> bool:
        """Store an incident record in Supabase."""
        try:
            data = asdict(incident)
            data['metadata'] = json.dumps(data['metadata'])
            
            result = self.client.table('incidents').upsert(data).execute()
            return len(result.data) > 0
        except Exception as e:
            print(f"Error storing incident in Supabase: {e}")
            return False
    
    def get_artifact(self, digest: str) -> Optional[ArtifactRecord]:
        """Retrieve an artifact by digest from Supabase."""
        try:
            result = self.client.table('artifacts').select('*').eq('digest', digest).execute()
            if result.data:
                row = result.data[0]
                # Handle metadata - it might already be a dict or a JSON string
                if isinstance(row.get('metadata'), str):
                    try:
                        row['metadata'] = json.loads(row['metadata'])
                    except json.JSONDecodeError:
                        row['metadata'] = {}
                elif not isinstance(row.get('metadata'), dict):
                    row['metadata'] = {}
                
                return ArtifactRecord(**row)
            return None
        except Exception as e:
            print(f"Error retrieving artifact from Supabase: {e}")
            return None
    
    def get_spans_by_order(self, order_id: str) -> List[SpanRecord]:
        """Get all spans for a specific order from Supabase."""
        try:
            result = self.client.table('spans').select('*').eq('order_id', order_id).execute()
            spans = []
            for row in result.data:
                # Handle attributes - it might already be a dict or a JSON string
                if isinstance(row.get('attributes'), str):
                    try:
                        row['attributes'] = json.loads(row['attributes'])
                    except json.JSONDecodeError:
                        row['attributes'] = {}
                elif not isinstance(row.get('attributes'), dict):
                    row['attributes'] = {}
                
                spans.append(SpanRecord(**row))
            return spans
        except Exception as e:
            print(f"Error retrieving spans from Supabase: {e}")
            return []
    
    def get_incidents_by_order(self, order_id: str) -> List[IncidentRecord]:
        """Get all incidents for a specific order from Supabase."""
        try:
            result = self.client.table('incidents').select('*').eq('order_id', order_id).execute()
            incidents = []
            for row in result.data:
                # Handle metadata - it might already be a dict or a JSON string
                if isinstance(row.get('metadata'), str):
                    try:
                        row['metadata'] = json.loads(row['metadata'])
                    except json.JSONDecodeError:
                        row['metadata'] = {}
                elif not isinstance(row.get('metadata'), dict):
                    row['metadata'] = {}
                
                incidents.append(IncidentRecord(**row))
            return incidents
        except Exception as e:
            print(f"Error retrieving incidents from Supabase: {e}")
            return []
    
    def get_all_incidents(self) -> List[IncidentRecord]:
        """Get all incidents from Supabase."""
        try:
            result = self.client.table('incidents').select('*').execute()
            incidents = []
            for row in result.data:
                # Handle metadata - it might already be a dict or a JSON string
                if isinstance(row.get('metadata'), str):
                    try:
                        row['metadata'] = json.loads(row['metadata'])
                    except json.JSONDecodeError:
                        row['metadata'] = {}
                elif not isinstance(row.get('metadata'), dict):
                    row['metadata'] = {}
                
                incidents.append(IncidentRecord(**row))
            return incidents
        except Exception as e:
            print(f"Error retrieving all incidents from Supabase: {e}")
            return []
    
    def get_incident_by_id(self, incident_id: str) -> Optional[IncidentRecord]:
        """Get a specific incident by ID."""
        try:
            result = self.client.table('incidents').select('*').eq('incident_id', incident_id).execute()
            if result.data:
                row = result.data[0]
                # Handle metadata - it might already be a dict or a JSON string
                if isinstance(row.get('metadata'), str):
                    try:
                        row['metadata'] = json.loads(row['metadata'])
                    except json.JSONDecodeError:
                        row['metadata'] = {}
                elif not isinstance(row.get('metadata'), dict):
                    row['metadata'] = {}
                
                return IncidentRecord(**row)
            return None
        except Exception as e:
            print(f"Error retrieving incident from Supabase: {e}")
            return None

# -----------------------------------------------------------------------------
# Backend Service
# -----------------------------------------------------------------------------

class AgentOpsBackend:
    """Main backend service for AgentOps."""
    
    def __init__(self, database: SupabaseDatabase, artifacts_dir: str = "artifacts"):
        self.database = database
        self.artifacts_dir = Path(artifacts_dir)
        self.artifacts_dir.mkdir(exist_ok=True)
    
    def store_artifacts(self, artifacts: Dict[str, Any]) -> bool:
        """Store multiple artifacts in the database."""
        if not artifacts:
            print("⚠️  No artifacts provided for storage")
            return False
        
        print(f"💾 Storing {len(artifacts)} artifacts in Supabase...")
        success_count = 0
        
        for artifact_name, artifact_data in artifacts.items():
            try:
                # Create artifact record
                artifact_record = ArtifactRecord(
                    digest=artifact_name,
                    mime_type=artifact_data.mime_type,
                    length=artifact_data.length,
                    pii_masked=artifact_data.pii_masked,
                    created_at=artifact_data.created_at,
                    file_path=artifact_data.file_path,
                    metadata=artifact_data.metadata
                )
                
                # Store in database
                if self.database.store_artifact(artifact_record):
                    success_count += 1
                else:
                    print(f"  ❌ Failed to store artifact: {artifact_name}")
                    
            except Exception as e:
                print(f"  ❌ Error processing artifact {artifact_name}: {e}")
                continue
        
        print(f"📊 Artifact storage complete: {success_count}/{len(artifacts)} successful")
        return success_count > 0
    
    def store_spans(self, spans: List[Any], order_id: str) -> bool:
        """Store spans from the AgentOps run."""
        try:
            for span_data in spans:
                # Create span record
                span_record = SpanRecord(
                    span_id=span_data.span_id,
                    parent_id=span_data.parent_id,
                    tool=span_data.tool,
                    start_ts=span_data.start_ts,
                    end_ts=span_data.end_ts,
                    args_digest=span_data.args_digest,
                    result_digest=span_data.result_digest,
                    attributes=span_data.attributes,
                    created_at=datetime.utcnow().isoformat(),
                    order_id=order_id  # Link to order
                )
                
                # Store in database
                if not self.database.store_span(span_record):
                    print(f"Failed to store span {span_data.span_id}")
                    return False
            
            return True
        except Exception as e:
            print(f"Error storing spans: {e}")
            return False
    
    def create_incident(self, order_id: str, incident_type: str, eta_delta_hours: Optional[float], 
                       description: str, severity: str = "medium") -> bool:
        """Create an incident record."""
        try:
            incident_record = IncidentRecord(
                incident_id=f"inc_{order_id}_{int(datetime.utcnow().timestamp())}",
                order_id=order_id,
                incident_type=incident_type,
                severity=severity,
                status="open",
                eta_delta_hours=eta_delta_hours,
                description=description,
                created_at=datetime.utcnow().isoformat(),
                resolved_at=None,
                metadata={
                    "created_by": "agentops",
                    "source": "automated_detection"
                }
            )
            
            return self.database.store_incident(incident_record)
        except Exception as e:
            print(f"Error creating incident: {e}")
            return False
    
    def get_order_summary(self, order_id: str) -> Dict[str, Any]:
        """Get a comprehensive summary of an order including artifacts, spans, and incidents."""
        try:
            # Get incidents
            incidents = self.database.get_incidents_by_order(order_id)
            
            # Get spans
            spans = self.database.get_spans_by_order(order_id)
            
            return {
                "order_id": order_id,
                "incidents": [asdict(incident) for incident in incidents],
                "spans_count": len(spans),
                "spans": [asdict(span) for span in spans],
                "last_updated": datetime.utcnow().isoformat()
            }
        except Exception as e:
            print(f"Error getting order summary: {e}")
            return {}
    
    def get_incident_details(self, incident_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific incident."""
        try:
            incident = self.database.get_incident_by_id(incident_id)
            if incident:
                # Get related spans
                spans = self.database.get_spans_by_order(incident.order_id)
                
                return {
                    "incident": asdict(incident),
                    "related_spans": [asdict(span) for span in spans],
                    "spans_count": len(spans)
                }
            return None
        except Exception as e:
            print(f"Error getting incident details: {e}")
            return None

# -----------------------------------------------------------------------------
# Main Function
# -----------------------------------------------------------------------------

def main():
    """Main function to demonstrate the backend functionality."""
    
    # Check for Supabase credentials
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_KEY')
    
    if not supabase_url or not supabase_key:
        print("❌ Supabase credentials not found!")
        print("Please set environment variables:")
        print("export SUPABASE_URL='your-supabase-url'")
        print("export SUPABASE_KEY='your-supabase-anon-key'")
        return
    
    # Initialize database
    print("Initializing AgentOps Backend...")
    try:
        db = SupabaseDatabase(supabase_url, supabase_key)
        backend = AgentOpsBackend(db)
        print("✅ Backend initialized successfully!")
        print("📊 Database: Supabase")
        print("📁 Artifacts directory: artifacts/")
    except Exception as e:
        print(f"❌ Failed to initialize backend: {e}")
        return
    
    # Example usage
    print("\n🔍 Example: Creating an incident for order PO123...")
    success = backend.create_incident(
        order_id="PO123",
        incident_type="delivery_delay",
        eta_delta_hours=2.0,
        description="Order delivered 2 hours later than carrier ETA",
        severity="medium"
    )
    
    if success:
        print("✅ Incident created successfully!")
        
        # Get order summary
        summary = backend.get_order_summary("PO123")
        print(f"📋 Order Summary: {json.dumps(summary, indent=2)}")
    else:
        print("❌ Failed to create incident")
    
    print("\n🚀 Backend is ready for integration with AgentOps!")

if __name__ == "__main__":
    main()