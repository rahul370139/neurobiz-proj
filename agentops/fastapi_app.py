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

# Import our existing AgentOps implementation
from agent_ops import AgentOps
from extract_edi import extract_edi_from_html
from csv_compatibility import parse_erp_csv_compatible, parse_carrier_csv_compatible

def install_dependencies():
    """Install required dependencies."""
    print("📦 Installing dependencies...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ Dependencies installed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        return False

def check_dependencies():
    """Check if required packages are available."""
    required_packages = ['fastapi', 'uvicorn']
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    return missing_packages

def test_data_sample_org():
    """Test the data_sample_org data with AgentOps."""
    print("🧪 Testing data_sample_org Data with AgentOps")
    
    # Get the current directory
    base_dir = Path(__file__).resolve().parent
    data_dir = base_dir / "data_sample_org"
    
    if not data_dir.exists():
        print(f"❌ Data directory not found: {data_dir}")
        return False
    
    # List available files
    required_files = [
        "po_850_raw.edi",    # EDI 850 Purchase Order
        "asn_856_raw.edi",   # EDI 856 Advanced Shipping Notice
        "erp_iway.csv",      # ERP data
        "carrier_iway.csv"   # Carrier ETA data
    ]
    
    missing_files = []
    for file_name in required_files:
        file_path = data_dir / file_name
        if not file_path.exists():
            missing_files.append(file_name)
    
    if missing_files:
        print(f"❌ Missing required files: {', '.join(missing_files)}")
        return False
    
    print("✅ All required files found!")
    
    # Test AgentOps initialization
    try:
        agent = AgentOps(base_dir, data_dir_name="data_sample_org")
        print("✅ AgentOps initialized successfully!")
        return True
    except Exception as e:
        print(f"❌ Failed to initialize AgentOps: {e}")
        return False

# Initialize FastAPI app
app = FastAPI(
    title="AgentOps FastAPI Integration",
    description="Web interface for AgentOps EDI analysis",
    version="1.0.0"
)

# Create temporary directory for uploads
UPLOAD_DIR = Path("temp_uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# Data directory for processing - will use data_sample_org for testing
DATA_DIR = Path("data_sample_org")

# Track if we have uploaded data
HAS_UPLOADED_DATA = False

class AnalysisResult(BaseModel):
    order_id: str
    incidents_count: int
    processing_steps: int
    artifacts_generated: bool
    com_json: dict
    rca_json: dict
    spans: List[dict]

class UploadResponse(BaseModel):
    message: str
    files_processed: List[str]
    next_step: str

@app.on_event("startup")
async def startup_event():
    """Handle startup tasks including dependency checks and data validation."""
    print("🚀 AgentOps FastAPI Starting Up")
    print("=" * 50)
    
    # Check current directory
    current_dir = Path.cwd()
    print(f"📁 Current directory: {current_dir}")
    
    # Check if we're in the right directory
    if not (current_dir / "agent_ops.py").exists():
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
    
    # Test the data first
    print("\n🧪 Testing data_sample_org data...")
    try:
        if test_data_sample_org():
            print("✅ Data test passed!")
        else:
            print("❌ Data test failed!")
            print("\nContinuing anyway...")
    except Exception as e:
        print(f"⚠️ Could not run data test: {e}")
        print("Continuing anyway...")
    
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
    """Handle file uploads and process them."""
    global HAS_UPLOADED_DATA
    
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")
    
    processed_files = []
    
    for file in files:
        if file.filename:
            # Save uploaded file
            file_path = UPLOAD_DIR / file.filename
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            # Process based on file type
            if file.filename.endswith('.html'):
                # Extract EDI from HTML
                edi_filename = file.filename.replace('.html', '_raw.edi')
                edi_path = DATA_DIR / edi_filename
                if extract_edi_from_html(file_path, edi_path):
                    processed_files.append(f"EDI extracted from {file.filename}")
                    HAS_UPLOADED_DATA = True
            else:
                # Copy to data directory
                dest_path = DATA_DIR / file.filename
                shutil.copy2(file_path, dest_path)
                processed_files.append(f"Uploaded {file.filename}")
                HAS_UPLOADED_DATA = True
    
    return UploadResponse(
        message=f"Successfully processed {len(processed_files)} files",
        files_processed=processed_files,
        next_step="Analysis will start automatically in a few seconds..."
    )

@app.post("/analyze", response_model=AnalysisResult)
async def run_analysis():
    """Run AgentOps analysis on the uploaded data."""
    try:
        # Initialize AgentOps
        base_dir = Path(__file__).resolve().parent
        
        # Check if we have uploaded files, otherwise use data_sample_org for testing
        if HAS_UPLOADED_DATA and DATA_DIR.exists() and any(DATA_DIR.glob("*")):
            # Use uploaded data
            agent = AgentOps(base_dir, data_dir_name="data_sample_org")
        else:
            # Fall back to data_sample_org for testing
            agent = AgentOps(base_dir, data_dir_name="data_sample_org")
        
        # Run analysis
        com_json, rca_json, spans = agent.run()
        
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
        
        return AnalysisResult(
            order_id=com_json.get('order_id', {}).get('value', 'N/A'),
            incidents_count=1 if rca_json.get('status') != 'no_incident' else 0,
            processing_steps=len(spans),
            artifacts_generated=len(spans) > 0,
            com_json=com_json,
            rca_json=rca_json,
            spans=spans_data
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "AgentOps FastAPI"}

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
    if DATA_DIR.exists():
        for file_path in DATA_DIR.glob("*"):
            if file_path.is_file():
                files.append({
                    "name": file_path.name,
                    "type": "processed",
                    "size": file_path.stat().st_size
                })
    
    return {"files": files}

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
