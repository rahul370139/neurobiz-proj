# AgentOps FastAPI Integration

This document describes the FastAPI frontend integration for AgentOps, which provides a web interface for uploading EDI and CSV files and running analysis.

## 🚀 Quick Start

### Option 1: Automated Startup (Recommended)
```bash
cd agentops
python3 start_fastapi.py
```

This script will:
- Check and install dependencies automatically
- Test the data_sample_org data
- Start the FastAPI server

### Option 2: Manual Setup
```bash
cd agentops
pip install -r requirements.txt
python3 fastapi_app.py
```

## 🌐 Web Interface

Once the server is running, you can access:

- **Main Interface**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

## 📁 File Upload

The web interface supports uploading:

- **EDI files** (.edi) - Purchase Orders (850), Shipping Notices (856)
- **CSV files** (.csv) - ERP data, Carrier data  
- **HTML files** (.html) - Will be processed to extract EDI content

## 🔧 How It Works

### 1. File Upload & Preprocessing
- Files are uploaded via the web interface
- HTML files are processed using `extract_edi.py` to extract EDI content
- Files are stored temporarily for processing

### 2. AgentOps Analysis
- The uploaded files are processed by the existing `AgentOps` class
- Analysis generates:
  - Canonical Order Model (COM)
  - Root Cause Analysis (RCA)
  - Execution spans
  - Artifacts

### 3. Results Display
- Results are displayed in an interactive web interface
- JSON data is formatted for easy reading
- Artifacts are generated in the `artifacts/` folder

## 🧪 Testing

### Test Existing Data
```bash
python3 test_data_sample_org.py
```

This tests the existing `data_sample_org` data to ensure it works correctly.

### Test File Upload
1. Start the FastAPI server
2. Open http://localhost:8000
3. Upload test files
4. Run analysis
5. View results

## 📊 API Endpoints

### GET /
- **Description**: Main upload page
- **Response**: HTML interface for file upload

### POST /upload
- **Description**: Upload files for processing
- **Parameters**: `files` (multipart file upload)
- **Response**: Upload confirmation and file list

### POST /analyze
- **Description**: Run AgentOps analysis on uploaded files
- **Response**: Analysis results (COM, RCA, spans)

### GET /health
- **Description**: Health check endpoint
- **Response**: Server status

### GET /files
- **Description**: List currently uploaded files
- **Response**: List of file names

## 🔍 Troubleshooting

### Common Issues

1. **Dependencies not installed**
   ```bash
   pip install -r requirements.txt
   ```

2. **Port 8000 already in use**
   - Change the port in `fastapi_app.py`
   - Or stop other services using port 8000

3. **Data test fails**
   - Ensure `data_sample_org` directory exists
   - Check that required files are present
   - Verify file permissions

4. **File upload fails**
   - Check file formats (supported: .edi, .csv, .html)
   - Ensure files are not corrupted
   - Check disk space

### Debug Mode

For detailed error information, check the console output when running the server.

## 📁 File Structure

```
agentops/
├── fastapi_app.py          # FastAPI web application
├── start_fastapi.py        # Automated startup script
├── test_data_sample_org.py # Data testing script
├── agent_ops.py            # Core AgentOps implementation
├── extract_edi.py          # EDI extraction utility
├── main.py                 # Command-line interface
├── requirements.txt        # Python dependencies
├── data_sample_org/        # Sample data directory
├── artifacts/              # Generated artifacts
└── README_FASTAPI.md       # This file
```

## 🔄 Integration with Existing Code

The FastAPI integration:

- **Preserves** all existing AgentOps functionality
- **Uses** the same `AgentOps` class and `extract_edi.py` utility
- **Maintains** the same data processing pipeline
- **Adds** web interface capabilities

## 🚀 Next Steps

After successful testing:

1. **Customize the web interface** for your specific needs
2. **Add authentication** if required
3. **Integrate with your existing systems**
4. **Deploy to production** environment

## 📞 Support

For issues or questions:

1. Check the troubleshooting section above
2. Review the console output for error messages
3. Test with the provided sample data first
4. Ensure all dependencies are properly installed
