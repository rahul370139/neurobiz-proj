# AgentOps FastAPI Application

A flexible FastAPI application for analyzing EDI and CSV files using AgentOps. This application allows users to upload their own files for analysis without requiring specific hardcoded file names.

## Features

- **Flexible File Upload**: Accepts any EDI (.edi), CSV (.csv), or HTML files
- **Automatic File Processing**: Automatically detects and processes different file types
- **Smart EDI Detection**: Automatically identifies EDI 850 (Purchase Order) vs 856 (Shipping Notice) files
- **CSV Compatibility**: Handles various CSV formats with automatic column detection
- **Real-time Analysis**: Runs AgentOps analysis on uploaded files
- **Health Monitoring**: Comprehensive health checks and status endpoints
- **Storage Integration**: Optional Supabase integration for storing results

## Quick Start

### 1. Deploy to Railway

The application is configured for Railway deployment with:
- `Procfile` for process management
- `railway.json` for deployment configuration
- `requirements.txt` for Python dependencies

### 2. Access the Application

Once deployed, you can:
- **Web Interface**: Visit the root URL `/` to upload files
- **API Documentation**: Visit `/docs` for interactive API documentation
- **Health Check**: Visit `/health` to check application status
- **Test Endpoint**: Visit `/test` to verify the application is running

### 3. Upload Files

Upload any combination of:
- **EDI Files**: `.edi` files (automatically detected as 850 or 856)
- **CSV Files**: `.csv` files (automatically detected as ERP or carrier data)
- **HTML Files**: `.html` files containing EDI content (automatically extracted)

### 4. Run Analysis

After uploading files, use the `/analyze` endpoint to run AgentOps analysis.

## API Endpoints

- `GET /` - File upload web interface
- `POST /upload` - Upload EDI/CSV files
- `POST /analyze` - Run analysis on uploaded files
- `GET /health` - Application health and status
- `GET /test` - Simple test endpoint
- `GET /files` - List uploaded files
- `GET /docs` - Interactive API documentation

## File Requirements

The application is designed to work with any files you upload. It automatically:

- **Detects EDI file types** (850 vs 856) based on content
- **Processes CSV files** with automatic column detection
- **Extracts EDI content** from HTML files
- **Creates the necessary data structure** for AgentOps analysis

## Deployment Notes

- **No Hardcoded Files Required**: The application starts successfully without requiring specific sample files
- **Flexible Data Handling**: Works with any combination of uploaded files
- **Graceful Degradation**: Continues to function even with missing data types
- **Automatic Cleanup**: Manages temporary files and directories automatically

## Environment Variables

Optional environment variables for enhanced functionality:
- `SUPABASE_URL` - For Supabase storage integration
- `SUPABASE_KEY` - For Supabase authentication

## Troubleshooting

### Common Issues

1. **"No files available for analysis"**
   - Upload files first using the `/upload` endpoint
   - Ensure files are in supported formats (.edi, .csv, .html)

2. **Analysis fails with 500 error**
   - Check that uploaded files contain valid data
   - Verify file formats are supported
   - Check application logs for specific error details

3. **Missing data types warning**
   - This is normal and won't prevent analysis
   - Upload additional file types for optimal results

### Health Check

Use the `/health` endpoint to diagnose issues:
- Check file upload directory status
- Verify parsed data availability
- Monitor storage integration status

## Development

To run locally:
```bash
cd agentops
python3 fastapi_app.py
```

The application will start on `http://localhost:8000` with automatic dependency installation.
