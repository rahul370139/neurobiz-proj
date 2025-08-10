#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unified FastAPI Application for AgentOps

This FastAPI application provides a web interface for uploading EDI and CSV files
and running AgentOps analysis. It integrates with the existing AgentOps implementation
and includes built-in startup and dependency management.
"""

import os
import tempfile
import shutil
import subprocess
import sys
from pathlib import Path
from typing import List, Optional
from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn
import json
import datetime

# Import our existing AgentOps implementation
from agent_ops import AgentOps
from extract_edi import extract_edi_from_html
from csv_compatibility import parse_erp_csv_compatible, parse_carrier_csv_compatible

# Import storage integration
try:
    from storage_integration import FastAPIStorageIntegration
    STORAGE_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Storage integration not available: {e}")
    STORAGE_AVAILABLE = False

def check_dependencies():
    """Check if required packages are available."""
    required_packages = [
        "fastapi",
        "uvicorn",
        "python-multipart",
        "jinja2"
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    return missing_packages

def install_dependencies():
    """Install missing dependencies."""
    try:
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        return True
    except Exception as e:
        print(f"Failed to install dependencies: {e}")
        return False

# Initialize FastAPI app
app = FastAPI(
    title="AgentOps FastAPI Integration",
    description="Web interface for AgentOps EDI analysis",
    version="1.0.0"
)

# Create temporary directory for uploads
UPLOAD_DIR = Path(__file__).resolve().parent / "temp_uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

# Data directory for processing - will be created dynamically based on uploads
DATA_DIR = None

# Track if we have uploaded data
HAS_UPLOADED_DATA = False

# Store parsed data from uploads
UPLOADED_PARSED_DATA = {}

class StorageResults(BaseModel):
    """Model for storage operation results."""
    success: bool
    artifacts_stored: int
    spans_stored: int
    incident_created: bool
    order_id: str
    error: Optional[str] = None

class AnalysisResult(BaseModel):
    order_id: str
    incidents_count: int
    processing_steps: int
    artifacts_generated: bool
    com_json: dict
    rca_json: dict
    spans: List[dict]
    storage_results: Optional[StorageResults] = None  # Updated to use specific model

class UploadResponse(BaseModel):
    message: str
    files_processed: List[str]
    next_step: str

@app.on_event("startup")
async def startup_event():
    """Handle startup tasks including dependency checks and data validation."""
    print("🚀 AgentOps FastAPI Starting Up")
    print("=" * 50)
    
    # Check script directory instead of current working directory
    script_dir = Path(__file__).resolve().parent
    print(f"📁 Script directory: {script_dir}")
    print(f"📁 Current working directory: {Path.cwd()}")
    
    # Check if we're in the right directory (use script location)
    if not (script_dir / "agent_ops.py").exists():
        print("❌ Please run this script from the agentops directory")
        print("   cd agentops")
        print("   python3 fastapi_app.py")
        sys.exit(1)
    
    # Check dependencies
    print("\n🔍 Checking dependencies...")
    missing_packages = check_dependencies()
    
    if missing_packages:
        print(f"❌ Missing packages: {', '.join(missing_packages)}")
        print("Installing dependencies...")
        if not install_dependencies():
            print("❌ Failed to install dependencies. Please install manually:")
            print("   pip install -r requirements.txt")
            sys.exit(1)
    else:
        print("✅ All dependencies are available!")
    
    # Initialize storage integration if available
    global storage_integration
    if STORAGE_AVAILABLE:
        print("\n💾 Initializing storage integration...")
        try:
            storage_integration = FastAPIStorageIntegration()
            if storage_integration.is_available():
                print("✅ Supabase storage integration ready!")
            else:
                print("⚠️  Storage integration not available")
        except Exception as e:
            print(f"⚠️  Storage integration failed: {e}")
    else:
        print("⚠️  Storage integration not available")
        storage_integration = None
    
    print("\n🌐 FastAPI server ready!")
    print("📚 API documentation available at: /docs")
    print("🌍 Web interface available at: /")
    print("-" * 50)

@app.get("/", response_class=HTMLResponse)
async def get_upload_page():
    """Serve the main upload page."""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>AgentOps File Upload</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
            .upload-section { border: 2px dashed #ccc; padding: 20px; margin: 20px 0; text-align: center; }
            .file-input { margin: 10px 0; }
            .submit-btn { background: #007bff; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; }
            .submit-btn:hover { background: #0056b3; }
            .status { margin: 20px 0; padding: 10px; border-radius: 5px; }
            .success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
            .error { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
            .info { background: #d1ecf1; color: #0c5460; border: 1px solid #bee5eb; }
        </style>
    </head>
    <body>
        <h1>🚀 AgentOps File Upload & Analysis</h1>
        
        <div class="upload-section">
            <h3>📁 Upload EDI and CSV Files</h3>
            <p>Upload your EDI and CSV files for analysis. Supported formats:</p>
            <ul style="text-align: left; display: inline-block;">
                <li>EDI files (.edi) - Purchase Orders (850), Shipping Notices (856)</li>
                <li>CSV files (.csv) - ERP data, Carrier data</li>
                <li>HTML files (.html) - Will be processed to extract EDI content</li>
            </ul>
            
            <form id="uploadForm" enctype="multipart/form-data">
                <div class="file-input">
                    <label for="files">Select files:</label><br>
                    <input type="file" id="files" name="files" multiple accept=".edi,.csv,.html,.txt" required>
                </div>
                <button type="submit" class="submit-btn">🚀 Start Analysis</button>
            </form>
        </div>
        
        <div id="status"></div>
        <div id="results"></div>
        
        <script>
            document.getElementById('uploadForm').addEventListener('submit', async (e) => {
                e.preventDefault();
                
                const formData = new FormData();
                const fileInput = document.getElementById('files');
                const files = fileInput.files;
                
                if (files.length === 0) {
                    showStatus('Please select at least one file.', 'error');
                    return;
                }
                
                for (let i = 0; i < files.length; i++) {
                    formData.append('files', files[i]);
                }
                
                showStatus('Uploading files...', 'info');
                
                try {
                    const response = await fetch('/upload', {
                        method: 'POST',
                        body: formData
                    });
                    
                    const result = await response.json();
                    
                    if (response.ok) {
                        showStatus(result.message, 'success');
                        showNextStep(result.next_step);
                        
                        // Auto-run analysis after successful upload
                        setTimeout(() => {
                            runAnalysis();
                        }, 2000);
                    } else {
                        showStatus('Upload failed: ' + result.detail, 'error');
                    }
                } catch (error) {
                    showStatus('Upload error: ' + error.message, 'error');
                }
            });
            
            async function runAnalysis() {
                showStatus('Running analysis...', 'info');
                
                try {
                    const response = await fetch('/analyze', {
                        method: 'POST'
                    });
                    
                    const result = await response.json();
                    
                    if (response.ok) {
                        showStatus('Analysis completed successfully!', 'success');
                        showResults(result);
                    } else {
                        showStatus('Analysis failed: ' + result.detail, 'error');
                    }
                } catch (error) {
                    showStatus('Analysis error: ' + error.message, 'error');
                }
            }
            
            function showStatus(message, type) {
                const statusDiv = document.getElementById('status');
                statusDiv.innerHTML = `<div class="status ${type}">${message}</div>`;
            }
            
            function showNextStep(step) {
                const resultsDiv = document.getElementById('results');
                resultsDiv.innerHTML = `<div class="status info"><strong>Next:</strong> ${step}</div>`;
            }
            
            function showResults(result) {
                const resultsDiv = document.getElementById('results');
                resultsDiv.innerHTML = `
                    <div class="status success">
                        <h3>📊 Analysis Results</h3>
                        <p><strong>Order ID:</strong> ${result.order_id}</p>
                        <p><strong>Incidents:</strong> ${result.incidents_count}</p>
                        <p><strong>Processing Steps:</strong> ${result.processing_steps}</p>
                        <p><strong>Artifacts Generated:</strong> ${result.artifacts_generated ? 'Yes' : 'No'}</p>
                    </div>
                `;
            }
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.post("/upload", response_model=UploadResponse)
async def upload_files(files: List[UploadFile] = File(...)):
    """Upload and process EDI and CSV files."""
    global HAS_UPLOADED_DATA
    
    try:
        print(f"📁 Upload endpoint called with {len(files)} files")
        print(f"📁 UPLOAD_DIR: {UPLOAD_DIR}")
        
        # Create a unique data directory for this upload session
        global DATA_DIR
        if DATA_DIR is None:
            DATA_DIR = Path(__file__).resolve().parent / f"upload_data_{int(datetime.datetime.now().timestamp())}"
        DATA_DIR.mkdir(exist_ok=True)
        print(f"📁 DATA_DIR: {DATA_DIR}")
        
        processed_files = []
        parsed_data = {}
        
        for file in files:
            if file.filename:
                print(f"📄 Processing file: {file.filename}")
                
                # Save uploaded file
                file_path = UPLOAD_DIR / file.filename
                print(f"💾 Saving to: {file_path}")
                
                with open(file_path, "wb") as buffer:
                    shutil.copyfileobj(file.file, buffer)
                
                print(f"✅ File saved successfully: {file_path}")
                
                # Process based on file type
                if file.filename.endswith('.html'):
                    # Extract EDI from HTML
                    edi_filename = file.filename.replace('.html', '_raw.edi')
                    edi_path = DATA_DIR / edi_filename
                    if extract_edi_from_html(file_path, edi_path):
                        processed_files.append(f"EDI extracted from {file.filename}")
                        HAS_UPLOADED_DATA = True
                        
                        # Parse the extracted EDI file
                        try:
                            from agent_ops import read_edi_file
                            edi_segments = read_edi_file(edi_path)
                            # Determine if this is 850 or 856 based on content
                            if any('850' in segment[0] for segment in edi_segments if segment):
                                parsed_data['edi_850'] = edi_segments
                            elif any('856' in segment[0] for segment in edi_segments if segment):
                                parsed_data['edi_856'] = edi_segments
                            else:
                                # Default to 850 if can't determine
                                if 'edi_850' not in parsed_data:
                                    parsed_data['edi_850'] = edi_segments
                                else:
                                    parsed_data['edi_856'] = edi_segments
                        except Exception as e:
                            print(f"⚠️  Could not parse EDI file: {e}")
                elif file.filename.endswith('.edi'):
                    # Copy EDI file directly
                    dest_path = DATA_DIR / file.filename
                    shutil.copy2(file_path, dest_path)
                    processed_files.append(f"Uploaded {file.filename}")
                    HAS_UPLOADED_DATA = True
                    
                    # Parse the EDI file
                    try:
                        from agent_ops import read_edi_file
                        edi_segments = read_edi_file(dest_path)
                        # Determine if this is 850 or 856 based on content
                        if any('850' in segment[0] for segment in edi_segments if segment):
                            parsed_data['edi_850'] = edi_segments
                        elif any('856' in segment[0] for segment in edi_segments if segment):
                            parsed_data['edi_856'] = edi_segments
                        else:
                            # Default to 850 if can't determine
                            if 'edi_850' not in parsed_data:
                                parsed_data['edi_850'] = edi_segments
                            else:
                                parsed_data['edi_856'] = edi_segments
                    except Exception as e:
                        print(f"⚠️  Could not parse EDI file: {e}")
                elif file.filename.endswith('.csv'):
                    # Copy CSV file directly
                    dest_path = DATA_DIR / file.filename
                    shutil.copy2(file_path, dest_path)
                    processed_files.append(f"Uploaded {file.filename}")
                    HAS_UPLOADED_DATA = True
                    
                    # Parse the CSV file
                    try:
                        if 'erp' not in parsed_data:
                            # Try to parse as ERP data
                            erp_data = parse_erp_csv_compatible(dest_path)
                            parsed_data['erp'] = erp_data
                        elif 'carrier' not in parsed_data:
                            # Try to parse as carrier data
                            carrier_data = parse_carrier_csv_compatible(dest_path)
                            parsed_data['carrier'] = carrier_data
                    except Exception as e:
                        print(f"⚠️  Could not parse CSV file: {e}")
                else:
                    # Copy other file types
                    dest_path = DATA_DIR / file.filename
                    shutil.copy2(file_path, dest_path)
                    processed_files.append(f"Uploaded {file.filename}")
                    HAS_UPLOADED_DATA = True
                
                print(f"✅ File processed: {file.filename}")
        
        # Store parsed data globally for analysis
        global UPLOADED_PARSED_DATA
        UPLOADED_PARSED_DATA = parsed_data
        
        print(f"🎉 Successfully processed {len(processed_files)} files")
        print(f"📊 Parsed data keys: {list(parsed_data.keys())}")
        print("✅ Analysis will work with any combination of uploaded files!")
        
        return UploadResponse(
            message=f"Successfully processed {len(processed_files)} files",
            files_processed=processed_files,
            next_step="Analysis will start automatically in a few seconds..."
        )
        
    except Exception as e:
        print(f"❌ Error in upload endpoint: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@app.post("/analyze", response_model=AnalysisResult)
async def run_analysis():
    """Run AgentOps analysis on the uploaded data."""
    try:
        # Initialize AgentOps
        base_dir = Path(__file__).resolve().parent
        
        # Check if we have uploaded files with parsed data
        if HAS_UPLOADED_DATA and UPLOADED_PARSED_DATA and any(UPLOADED_PARSED_DATA.keys()):
            # Use uploaded parsed data directly
            print("📁 Using uploaded parsed data for analysis...")
            print(f"📊 Available data: {list(UPLOADED_PARSED_DATA.keys())}")
            
            # Create a flexible analysis approach that works with any data
            print("🔄 Running flexible analysis with available data...")
            
            # Generate mock data for missing types to satisfy AgentOps requirements
            # This allows the analysis to run with any combination of files
            flexible_data = UPLOADED_PARSED_DATA.copy()
            
            # Generate unique order ID for this analysis session
            unique_order_id = f"ORDER_{int(datetime.datetime.now().timestamp())}"
            
            # If we don't have edi_850, create a minimal one
            if 'edi_850' not in flexible_data:
                print("📝 Creating minimal EDI 850 data for analysis...")
                flexible_data['edi_850'] = [
                    ['BEG', '00', 'SA', unique_order_id, '', '20240101'],
                    ['DTM', '002', '20240101'],
                    ['N1', 'ST', 'Customer Name'],
                    ['PO1', '1', '10', 'EA', '10.00', 'VP', 'ITEM001']
                ]
            
            # If we don't have edi_856, create a minimal one
            if 'edi_856' not in flexible_data:
                print("📝 Creating minimal EDI 856 data for analysis...")
                flexible_data['edi_856'] = [
                    ['BSN', '00', f'SHIP_{unique_order_id}', '20240101', '1200'],
                    ['DTM', '011', '20240101'],
                    ['N1', 'ST', 'Customer Name'],
                    ['S5', '1', '10', 'EA']
                ]
            
            # If we don't have erp data, create minimal one
            if 'erp' not in flexible_data:
                print("📝 Creating minimal ERP data for analysis...")
                flexible_data['erp'] = {
                    unique_order_id: {
                        'order_date': '2024-01-01',
                        'customer_name': 'Customer Name',
                        'total_amount': '100.00'
                    }
                }
            
            # If we don't have carrier data, create minimal one
            if 'carrier' not in flexible_data:
                print("📝 Creating minimal carrier data for analysis...")
                flexible_data['carrier'] = {
                    unique_order_id: 'Standard Shipping'
                }
            
            print(f"✅ Flexible data prepared with keys: {list(flexible_data.keys())}")
            
            # Initialize AgentOps with the flexible data
            agent = AgentOps(base_dir, parsed_data=flexible_data)
            
        elif HAS_UPLOADED_DATA and DATA_DIR.exists() and any(DATA_DIR.glob("*")):
            # Use uploaded files - create a temporary directory with the uploaded files
            print("📁 Using uploaded files for analysis...")
            # Create a temporary working directory with uploaded files
            temp_work_dir = Path(__file__).resolve().parent / "temp_analysis"
            temp_work_dir.mkdir(exist_ok=True)
            
            # Copy uploaded files to temp directory
            for file_path in DATA_DIR.glob("*"):
                if file_path.is_file():
                    shutil.copy2(file_path, temp_work_dir / file_path.name)
            
            # Use the temp directory for analysis
            agent = AgentOps(base_dir, data_dir_name="temp_analysis")
        else:
            raise HTTPException(
                status_code=400, 
                detail="No files available for analysis. Please upload EDI/CSV files first using the /upload endpoint."
            )
        
        # Run analysis
        print("🔍 Running AgentOps analysis...")
        com_json, rca_json, spans = agent.run()
        print("✅ Analysis completed successfully!")
        
        # Clean up temporary directory if it was created
        temp_work_dir = Path(__file__).resolve().parent / "temp_analysis"
        if temp_work_dir.exists():
            try:
                shutil.rmtree(temp_work_dir)
                print("🧹 Cleaned up temporary analysis directory")
            except Exception as e:
                print(f"⚠️  Could not clean up temp directory: {e}")
        
        # Convert spans to serializable format
        spans_data = []
        for span in spans:
            spans_data.append({
                "span_id": span.span_id,
                "parent_id": span.parent_id,
                "tool": span.tool,
                "start_ts": span.start_ts,
                "end_ts": span.end_ts,
                "args_digest": span.args_digest,
                "result_digest": span.result_digest,
                "attributes": span.attributes
            })
        
        # Store results in Supabase if storage is available
        storage_results = None
        if storage_integration and storage_integration.is_available():
            print("\n💾 Storing analysis results in Supabase...")
            artifacts_dir = base_dir / "artifacts"
            
            # Ensure artifacts directory exists
            if not artifacts_dir.exists():
                print(f"⚠️  Artifacts directory not found: {artifacts_dir}")
                print("   This may indicate that AgentOps didn't generate artifacts")
            else:
                print(f"📁 Found artifacts directory: {artifacts_dir}")
                artifact_files = list(artifacts_dir.glob("*"))
                print(f"   Found {len(artifact_files)} artifact files")
            
            storage_results = storage_integration.store_analysis_results(
                com_json, rca_json, spans, artifacts_dir
            )
            
            if storage_results.get("success"):
                print(f"✅ Storage successful: {storage_results['artifacts_stored']} artifacts, "
                      f"{storage_results['spans_stored']} spans, "
                      f"incident: {storage_results['incident_created']}")
            else:
                print(f"⚠️  Storage issues: {storage_results.get('error', 'Unknown error')}")
        else:
            print("\n⚠️  Supabase storage not available")
            print("   Artifacts are only stored locally in the artifacts/ directory")
            print("   To enable Supabase storage, set SUPABASE_URL and SUPABASE_KEY environment variables")
        
        # Create response with storage info
        response = AnalysisResult(
            order_id=com_json.get('order_id', {}).get('value', 'N/A'),
            incidents_count=1 if rca_json.get('status') != 'no_incident' else 0,
            processing_steps=len(spans),
            artifacts_generated=len(spans) > 0,
            com_json=com_json,
            rca_json=rca_json,
            spans=spans_data
        )
        
        # Add storage results to response if available
        if storage_results:
            response.storage_results = StorageResults(**storage_results) # Convert dict to model
        
        return response
        
    except Exception as e:
        print(f"❌ Analysis failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

@app.get("/test")
async def test_endpoint():
    """Simple test endpoint to verify the application is working."""
    return {
        "message": "AgentOps FastAPI is running!",
        "status": "ok",
        "timestamp": datetime.datetime.now().isoformat(),
        "available_endpoints": [
            "/ - File upload interface",
            "/upload - Upload files endpoint",
            "/analyze - Run analysis endpoint",
            "/health - Health check",
            "/files - List uploaded files",
            "/docs - API documentation"
        ],
        "note": "Upload EDI/CSV files to get started with analysis"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint with directory status."""
    try:
        # Check directory status
        upload_dir_exists = UPLOAD_DIR.exists()
        data_dir_exists = DATA_DIR is not None and DATA_DIR.exists()
        
        # Check if directories are writable
        upload_writable = False
        data_writable = False
        
        if upload_dir_exists:
            try:
                test_file = UPLOAD_DIR / "test.txt"
                test_file.write_text("test")
                test_file.unlink()
                upload_writable = True
            except Exception as e:
                upload_writable = False
        
        if data_dir_exists and DATA_DIR is not None:
            try:
                test_file = DATA_DIR / "test.txt"
                test_file.write_text("test")
                test_file.unlink()
                data_writable = True
            except Exception as e:
                data_writable = False
        
        def list_files_in_dir(directory: Path) -> List[str]:
            """Helper to list files in a directory."""
            if not directory.exists():
                return []
            return [f.name for f in directory.iterdir() if f.is_file()]

        return {
            "status": "healthy",
            "timestamp": datetime.datetime.now().isoformat(),
            "upload_dir": {
                "path": str(UPLOAD_DIR),
                "exists": upload_dir_exists,
                "writable": upload_writable,
                "files": list_files_in_dir(UPLOAD_DIR) if upload_dir_exists else []
            },
            "data_dir": {
                "path": str(DATA_DIR),
                "exists": data_dir_exists,
                "writable": data_writable,
                "files": list_files_in_dir(DATA_DIR) if data_dir_exists else []
            },
            "uploaded_data": {
                "has_uploaded_data": HAS_UPLOADED_DATA,
                "parsed_data_keys": list(UPLOADED_PARSED_DATA.keys()) if UPLOADED_PARSED_DATA else [],
                "parsed_data_count": len(UPLOADED_PARSED_DATA) if UPLOADED_PARSED_DATA else 0
            },
            "storage": {
                "available": STORAGE_AVAILABLE,
                "integration_ready": storage_integration.is_available() if storage_integration else False
            }
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "service": "AgentOps FastAPI"
        }

@app.get("/files")
async def list_uploaded_files():
    """List all uploaded and processed files."""
    files = []
    
    # List files in upload directory
    if UPLOAD_DIR.exists():
        for file_path in UPLOAD_DIR.glob("*"):
            if file_path.is_file():
                files.append({
                    "name": file_path.name,
                    "type": "uploaded",
                    "size": file_path.stat().st_size
                })
    
    # List files in data directory
    if DATA_DIR is not None and DATA_DIR.exists():
        for file_path in DATA_DIR.glob("*"):
            if file_path.is_file():
                files.append({
                    "name": file_path.name,
                    "type": "processed",
                    "size": file_path.stat().st_size
                })
    
    return {"files": files}

@app.get("/storage/status")
async def get_storage_status():
    """Get the current status of Supabase storage integration."""
    if not storage_integration:
        return {
            "status": "not_available",
            "initialized": False,
            "message": "Storage integration module not available"
        }
    
    return {
        "status": "available" if storage_integration.is_available() else "not_available",
        "initialized": storage_integration.is_available(),
        "message": "Storage integration is working" if storage_integration.is_available() else "Storage integration not initialized"
    }

@app.get("/storage/incidents")
async def get_all_incidents():
    """Get all incidents from Supabase storage."""
    if not storage_integration or not storage_integration.is_available():
        raise HTTPException(status_code=503, detail="Storage not available")
    
    try:
        incidents = storage_integration.get_all_incidents()
        return {"incidents": incidents, "count": len(incidents)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve incidents: {str(e)}")

@app.get("/storage/order/{order_id}")
async def get_order_summary(order_id: str):
    """Get comprehensive summary of an order from Supabase storage."""
    if not storage_integration or not storage_integration.is_available():
        raise HTTPException(status_code=503, detail="Storage not available")
    
    try:
        summary = storage_integration.get_order_summary(order_id)
        if summary:
            return summary
        else:
            raise HTTPException(status_code=404, detail=f"Order {order_id} not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve order summary: {str(e)}")

def run_server():
    """Run the FastAPI server with uvicorn."""
    print("🌐 Starting FastAPI server...")
    print("📚 API documentation will be available at: http://localhost:8000/docs")
    print("🌍 Web interface will be available at: http://localhost:8000")
    print("⏹️  Press Ctrl+C to stop the server")
    print("-" * 50)
    
    uvicorn.run(app, host="0.0.0.0", port=8000)

if __name__ == "__main__":
    run_server()
