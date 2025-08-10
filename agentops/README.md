# AgentOps Core Implementation

This folder contains the core AgentOps system that processes supply chain data and generates actionable insights. It's the "brain" that analyzes EDI files, ERP data, and carrier information to detect problems and create solutions.

## What This Folder Achieves

### 🎯 **Core Functionality**
- **Data Ingestion**: Processes EDI 850 (purchase orders), EDI 856 (shipping notices), ERP CSV data, and carrier ETA information
- **Canonical Order Model (COM)**: Creates a unified, normalized view of order data with field-level provenance tracking
- **Root Cause Analysis (RCA)**: Automatically detects delivery delays and generates deterministic analysis reports
- **Incident Detection**: Identifies problems like ETA slips, wrong products, and payment delays
- **Email Generation**: Creates both internal notifications and customer-facing communications with automatic PII redaction

### 🔍 **Data Processing Pipeline**
1. **Parse EDI Files**: Extracts structured data from EDI 850/856 messages
2. **Merge ERP Data**: Combines with enterprise resource planning information
3. **Calculate ETA Deltas**: Compares expected vs. actual delivery times
4. **Generate Insights**: Creates comprehensive analysis and recommendations

### 📊 **Output Generation**
- **Content-Addressed Artifacts**: Stores all outputs with SHA-256 digests for immutability
- **Deterministic Spans**: Emits traceable execution logs with argument/result hashes
- **Structured JSON**: Produces COM, RCA, and span data in machine-readable format
- **Email Templates**: Generates notification drafts for stakeholders

## Project Structure

```
agentops/
├── agent_ops.py                    # Core AgentOps implementation class
├── main.py                         # Unified entry point with auto data detection
├── fastapi_app.py                  # Unified FastAPI web interface with startup management
├── extract_edi.py                  # Unified EDI utility with extraction and testing
├── csv_compatibility.py            # CSV compatibility layer for different formats
├── requirements.txt                # Python dependencies for FastAPI
├── README.md                       # This documentation
├── README_FASTAPI.md              # FastAPI-specific documentation
├── sample_data/                    # Sample input data for testing
│   ├── edi_850.txt                # Sample EDI 850 (Purchase Order)
│   ├── edi_856.txt                # Sample EDI 856 (Shipping Notice)
│   ├── erp.csv                    # Sample ERP data
│   ├── carrier.csv                # Sample carrier ETA data
│   └── templates/                 # Email templates
│       ├── internal_email.txt     # Internal notification template
│       └── customer_email.txt     # Customer notification template
├── data_sample_org/                # Alternative data format for testing
│   ├── po_850.edi                 # EDI 850 in HTML format
│   ├── asn_856.edi                # EDI 856 in HTML format
│   ├── erp_iway.csv               # ERP data with different column names
│   └── carrier_iway.csv           # Carrier data with different column names
└── artifacts/                      # Generated artifacts (created at runtime)
```

## Key Features

### 🚀 **Performance & Reliability**
- **Deterministic**: Same inputs always produce identical outputs
- **Self-contained**: No external dependencies for core functionality
- **Fault-tolerant**: Handles malformed data gracefully
- **Scalable**: Designed for processing multiple orders simultaneously
- **Auto-detection**: Automatically detects and uses available data directories

### 🔒 **Data Security**
- **PII Redaction**: Automatically masks sensitive information using regex patterns
- **Content Addressing**: SHA-256 hashes ensure data integrity and prevent tampering
- **Provenance Tracking**: Every data field shows its original source and transformation history

### 📈 **Observability**
- **Span Tracking**: Detailed operation logging for debugging and monitoring
- **Artifact Management**: Immutable storage with content-based addressing
- **Audit Trail**: Complete history of data transformations and decisions

### 🌐 **Web Interface**
- **FastAPI Integration**: Modern web API with automatic dependency management
- **File Upload**: Web interface for uploading and processing EDI/CSV files
- **Real-time Analysis**: Immediate processing and results display
- **Auto-startup**: Built-in dependency checking and installation

## How to Run

### Prerequisites
- Python 3.7 or higher
- For web interface: FastAPI and uvicorn (auto-installed)

### Quick Start - Command Line
```bash
cd agentops
python3 main.py
```

### Quick Start - Web Interface
```bash
cd agentops
python3 fastapi_app.py
```

### Data Validation and Testing
```bash
cd agentops
python3 extract_edi.py --test
```

### What Happens When You Run It
1. **Auto-detection**: Automatically finds and uses available data directories
2. **Data Loading**: Reads all available data files with format detection
3. **Processing**: Parses EDI, calculates delays, generates insights
4. **Output Creation**: Produces COM, RCA, and spans
5. **Artifact Storage**: Saves all outputs to `artifacts/` directory
6. **Console Display**: Shows results in formatted JSON

## Data Directory Support

The system automatically detects and works with multiple data formats:

### `sample_data/` (Standard Format)
- Standard EDI and CSV files
- Basic column names and structure

### `data_sample_org/` (Compatibility Format)
- EDI files embedded in HTML
- Different CSV column naming conventions
- Automatic compatibility layer handling

## Sample Data & Expected Results

### Input Data
- **EDI 850**: Purchase order PO123 with expected ship date 2025-08-02
- **EDI 856**: Shipping notice showing actual delivery on 2025-08-05 at 12:00
- **ERP Data**: Customer Acme Corporation, order value $100.00
- **Carrier Data**: ETA 2025-08-05 at 10:00 (2-hour delay detected)

### Generated Outputs
- **COM**: Unified order model with provenance for every field
- **RCA**: Analysis showing 2-hour delivery delay and root causes
- **Spans**: Execution trace showing each processing step
- **Artifacts**: Content-addressed files stored in `artifacts/` directory

## Integration Points

This core system is designed to work with:
- **Storage Backends**: Can connect to databases like Supabase for persistence
- **API Services**: Outputs structured data ready for REST endpoints
- **Web Interfaces**: Built-in FastAPI server for file upload and analysis
- **Testing Frameworks**: Comprehensive testing utilities for validation
