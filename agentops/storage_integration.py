#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Storage Integration for FastAPI App

This module integrates the FastAPI application with the Supabase storage system
to automatically store artifacts, spans, and incidents after each AgentOps analysis.
"""

import os
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import sys
import mimetypes
from dataclasses import asdict

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # Continue without dotenv if not available

try:
    from storage import SupabaseDatabase, AgentOpsBackend, ArtifactRecord, SpanRecord, IncidentRecord
    STORAGE_AVAILABLE = True
except ImportError as e:
    STORAGE_AVAILABLE = False
    print(f"Warning: Storage module not available: {e}")

class FastAPIStorageIntegration:
    """Integrates FastAPI with Supabase storage for AgentOps data."""
    
    def __init__(self):
        self.backend = None
        self.database = None
        self.initialized = False
        
        if STORAGE_AVAILABLE:
            self._initialize_storage()
    
    def _initialize_storage(self):
        """Initialize the Supabase storage backend."""
        try:
            supabase_url = os.getenv('SUPABASE_URL')
            supabase_key = os.getenv('SUPABASE_KEY')
            
            if not supabase_url or not supabase_key:
                print("⚠️  Supabase credentials not found. Storage will be disabled.")
                print("   Set environment variables: SUPABASE_URL and SUPABASE_KEY")
                return
            
            self.database = SupabaseDatabase(supabase_url, supabase_key)
            self.backend = AgentOpsBackend(self.database)
            self.initialized = True
            print("✅ Supabase storage initialized successfully")
            
        except Exception as e:
            print(f"❌ Failed to initialize Supabase storage: {e}")
            self.initialized = False
    
    def store_analysis_results(self, com_json: Dict[str, Any], rca_json: Dict[str, Any], 
                              spans: List[Any], artifacts_dir: Path) -> Dict[str, Any]:
        """
        Store the complete analysis results in Supabase.
        
        Args:
            com_json: Common Object Model data
            rca_json: Root Cause Analysis data
            spans: Execution spans
            artifacts_dir: Directory containing generated artifacts
            
        Returns:
            Dict containing storage results and status
        """
        if not self.initialized:
            return {
                "success": False,
                "error": "Storage not initialized",
                "artifacts_stored": 0,
                "spans_stored": 0,
                "incident_created": False
            }
        
        try:
            results = {
                "success": True,
                "artifacts_stored": 0,
                "spans_stored": 0,
                "incident_created": False,
                "order_id": "UNKNOWN"
            }
            
            # Extract order ID
            order_id = com_json.get("order_id", {}).get("value", "UNKNOWN")
            results["order_id"] = order_id
            
            # 1. Store artifacts
            print(f"💾 Storing artifacts for order {order_id}...")
            artifacts_data = self._prepare_artifacts_data(artifacts_dir)
            
            if artifacts_data:
                if self.backend.store_artifacts(artifacts_data):
                    results["artifacts_stored"] = len(artifacts_data)
                    print(f"✅ Stored {len(artifacts_data)} artifacts")
                else:
                    print("❌ Failed to store some artifacts")
            else:
                print("⚠️  No artifacts found to store")
            
            # 2. Store spans
            print(f"📊 Storing spans for order {order_id}...")
            if spans:
                if self.backend.store_spans(spans, order_id):
                    results["spans_stored"] = len(spans)
                    print(f"✅ Stored {len(spans)} spans")
                else:
                    print("❌ Failed to store some spans")
            else:
                print("⚠️  No spans found to store")
            
            # 3. Create incident if problems detected
            print(f"🚨 Creating incident record for order {order_id}...")
            if rca_json.get("status") != "no_incident":
                incident_created = self._create_incident_from_rca(rca_json, order_id)
                results["incident_created"] = incident_created
                
                if incident_created:
                    print("✅ Incident created successfully")
                else:
                    print("❌ Failed to create incident")
            else:
                print("ℹ️  No incidents detected")
            
            return results
            
        except Exception as e:
            print(f"❌ Error storing analysis results: {e}")
            return {
                "success": False,
                "error": str(e),
                "artifacts_stored": 0,
                "spans_stored": 0,
                "incident_created": False
            }
    
    def _prepare_artifacts_data(self, artifacts_dir: Path) -> Dict[str, Any]:
        """Prepare artifacts data for storage."""
        artifacts_data = {}
        
        if not artifacts_dir.exists():
            print(f"⚠️  Artifacts directory not found: {artifacts_dir}")
            return artifacts_data
        
        print(f"🔍 Scanning artifacts directory: {artifacts_dir}")
        
        for artifact_file in artifacts_dir.glob("*"):
            if artifact_file.is_file():
                try:
                    # Read the artifact content
                    with open(artifact_file, 'rb') as f:
                        content = f.read()
                    
                    # Determine MIME type based on file extension
                    mime_type = self._get_mime_type(artifact_file)
                    
                    # Check for PII indicators
                    pii_masked = self._check_pii_content(content.decode('utf-8', errors='ignore'))
                    
                    # Create artifact record
                    artifact_record = ArtifactRecord(
                        digest=artifact_file.name,  # Use filename as digest
                        mime_type=mime_type,
                        length=len(content),
                        pii_masked=pii_masked,
                        created_at=datetime.utcnow().isoformat(),
                        file_path=str(artifact_file),
                        metadata={
                            "source": "agent_ops",
                            "filename": artifact_file.name,
                            "file_size": len(content),
                            "created_by": "AgentOps Analysis"
                        }
                    )
                    
                    # Store directly in Supabase
                    if self.database.store_artifact(artifact_record):
                        artifacts_data[artifact_file.name] = artifact_record
                        print(f"  ✅ Stored artifact: {artifact_file.name}")
                    else:
                        print(f"  ❌ Failed to store artifact: {artifact_file.name}")
                        
                except Exception as e:
                    print(f"  ❌ Error processing artifact {artifact_file.name}: {e}")
                    continue
        
        print(f"📊 Total artifacts processed: {len(artifacts_data)}")
        return artifacts_data
    
    def _get_mime_type(self, file_path: Path) -> str:
        """Determine MIME type based on file extension."""
        mime_type, _ = mimetypes.guess_type(str(file_path))
        return mime_type or "application/octet-stream"
    
    def _check_pii_content(self, content: str) -> bool:
        """Check if content contains PII indicators."""
        pii_indicators = ['email', 'phone', 'ssn', 'credit_card', 'address']
        content_lower = content.lower()
        return any(indicator in content_lower for indicator in pii_indicators)
    
    def _create_incident_from_rca(self, rca_json: Dict[str, Any], order_id: str) -> bool:
        """Create an incident record from RCA data."""
        try:
            incident_type = self._determine_incident_type(rca_json)
            severity = self._determine_severity(rca_json)
            
            # Extract ETA delta if available
            eta_delta = None
            if "eta_delta_hours" in rca_json:
                eta_delta = rca_json["eta_delta_hours"]
            
            # Create incident description
            description = rca_json.get("why", "No description available")
            if eta_delta and eta_delta > 0:
                description = f"Delivery delay of {eta_delta} hours. {description}"
            
            incident_success = self.backend.create_incident(
                order_id=order_id,
                incident_type=incident_type,
                eta_delta_hours=eta_delta,
                description=description,
                severity=severity
            )
            
            return incident_success
            
        except Exception as e:
            print(f"❌ Error creating incident: {e}")
            return False
    
    def _determine_incident_type(self, rca_json: Dict[str, Any]) -> str:
        """Determine incident type from RCA data."""
        if "eta_delta_hours" in rca_json and rca_json["eta_delta_hours"] > 0:
            return "delivery_delay"
        elif "status" in rca_json and rca_json["status"] != "no_incident":
            return "data_discrepancy"
        else:
            return "other"
    
    def _determine_severity(self, rca_json: Dict[str, Any]) -> str:
        """Determine incident severity from RCA data."""
        if "eta_delta_hours" in rca_json:
            eta_delta = rca_json["eta_delta_hours"]
            if eta_delta > 24:
                return "high"
            elif eta_delta > 2:
                return "medium"
            else:
                return "low"
        return "medium"
    
    def get_order_summary(self, order_id: str) -> Optional[Dict[str, Any]]:
        """Get a summary of order data from Supabase."""
        if not self.initialized:
            return None
        
        try:
            return self.backend.get_order_summary(order_id)
        except Exception as e:
            print(f"❌ Error getting order summary: {e}")
            return None
    
    def get_all_incidents(self) -> List[Dict[str, Any]]:
        """Get all incidents from Supabase."""
        if not self.initialized:
            return []
        
        try:
            incidents = self.backend.database.get_all_incidents()
            return [asdict(incident) for incident in incidents]
        except Exception as e:
            print(f"❌ Error getting incidents: {e}")
            return []
    
    def is_available(self) -> bool:
        """Check if storage integration is available and initialized."""
        return self.initialized
