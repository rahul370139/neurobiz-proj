#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unified AgentOps Main Script

This script provides a flexible entry point for AgentOps that can handle data
from any source - uploaded files, specific directories, or dynamic inputs.
It automatically detects data formats and adapts processing accordingly.
"""

import csv
import json
import sys
import re
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional

# Import our AgentOps implementation and generic processors
from agent_ops import AgentOps
from csv_compatibility import csv_processor

# Import storage integration
try:
    from storage_integration import FastAPIStorageIntegration
    STORAGE_AVAILABLE = True
except ImportError as e:
    print(f"⚠️  Storage integration not available: {e}")
    STORAGE_AVAILABLE = False

class DynamicDataProcessor:
    """Dynamic data processor that can handle any data source and format."""
    
    def __init__(self):
        self.supported_formats = {
            'edi': ['.edi', '.txt'],
            'csv': ['.csv'],
            'html': ['.html', '.htm'],
            'html_edi': ['.edi', '.html', '.htm']  # Files that are HTML but contain EDI content
        }
    
    def detect_file_type(self, file_path: Path) -> str:
        """Detect file type based on extension and content."""
        if file_path.suffix.lower() in self.supported_formats['csv']:
            return 'csv'
        elif file_path.suffix.lower() in self.supported_formats['edi']:
            # Check content to determine if it's EDI or HTML with EDI content
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    first_line = f.readline().strip()
                    if first_line.startswith('ISA') or '*' in first_line:
                        return 'edi'
                    elif first_line.startswith('<!DOCTYPE') or first_line.startswith('<html'):
                        # Check if it contains EDI content in pre tags
                        content = f.read()
                        if '<pre' in content and '*' in content:
                            return 'html_edi'  # HTML file with EDI content
                        else:
                            return 'html'
                    else:
                        return 'text'
            except:
                return 'text'
        elif file_path.suffix.lower() in self.supported_formats['html']:
            # Check if HTML contains EDI content
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if '<pre' in content and '*' in content:
                        return 'html_edi'  # HTML file with EDI content
                    else:
                        return 'html'
            except:
                return 'html'
        else:
            return 'unknown'
    
    def extract_edi_file(self, file_path: Path) -> List[List[str]]:
        """Extract EDI file content into structured segments."""
        segments: List[List[str]] = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
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
        except Exception as e:
            print(f"❌ Error parsing EDI file {file_path}: {e}")
            return []
        return segments
    
    def extract_edi_from_html(self, file_path: Path) -> List[List[str]]:
        """Extract EDI content from HTML file with EDI content in pre tags."""
        segments: List[List[str]] = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Find the EDI content in the <pre> tags
            import re
            pre_match = re.search(r'<pre[^>]*>(.*?)</pre>', content, re.DOTALL)
            
            if pre_match:
                edi_content = pre_match.group(1).strip()
                
                # Process each line of EDI content
                for line in edi_content.split('\n'):
                    line = line.strip()
                    if not line or line.startswith("ISA") or line.startswith("GS") or line.startswith("GE") or line.startswith("IEA"):
                        # Skip envelope segments for this simple parser
                        continue
                    # Split on '*' and strip trailing '~' if present
                    if line.endswith("~"):
                        line = line[:-1]
                    parts = line.split("*")
                    segments.append(parts)
                
                print(f"      ✅ Extracted {len(segments)} EDI segments from HTML")
            else:
                print(f"      ⚠️  No EDI content found in HTML file")
                
        except Exception as e:
            print(f"❌ Error parsing HTML EDI file {file_path}: {e}")
            return []
        return segments
    
    def process_csv_file(self, file_path: Path, expected_types: List[str] = None) -> Dict[str, Any]:
        """Process CSV file using the generic CSV processor."""
        try:
            if expected_types:
                return csv_processor.parse_csv_generic(file_path, expected_types)
            else:
                return csv_processor.parse_csv_generic(file_path)
        except Exception as e:
            print(f"❌ Error processing CSV file {file_path}: {e}")
            return {"error": str(e)}
    
    def analyze_data_files(self, data_files: List[Path]) -> Dict[str, Any]:
        """Analyze a collection of data files and determine their types and content."""
        print(f"\n🔍 Analyzing {len(data_files)} data files...")
        
        analysis = {
            'files': {},
            'data_types': {
                'edi_850': None,
                'edi_856': None,
                'erp': None,
                'carrier': None
            },
            'summary': {
                'total_files': len(data_files),
                'processed_files': 0,
                'errors': 0
            }
        }
        
        for file_path in data_files:
            if file_path.is_file():
                file_type = self.detect_file_type(file_path)
                print(f"   📄 {file_path.name} -> {file_type}")
                
                file_analysis = {
                    'type': file_type,
                    'size': file_path.stat().st_size,
                    'processed': False,
                    'error': None
                }
                
                try:
                    if file_type == 'edi':
                        # Determine EDI type based on content or filename
                        if '850' in file_path.name.lower() or 'po' in file_path.name.lower():
                            segments = self.extract_edi_file(file_path)
                            analysis['data_types']['edi_850'] = segments
                            file_analysis['processed'] = True
                            file_analysis['segments'] = len(segments)
                            print(f"      ✅ Extracted EDI 850 with {len(segments)} segments")
                        elif '856' in file_path.name.lower() or 'asn' in file_path.name.lower():
                            segments = self.extract_edi_file(file_path)
                            analysis['data_types']['edi_856'] = segments
                            file_analysis['processed'] = True
                            file_analysis['segments'] = len(segments)
                            print(f"      ✅ Extracted EDI 856 with {len(segments)} segments")
                        else:
                            # Generic EDI processing
                            segments = self.extract_edi_file(file_path)
                            file_analysis['processed'] = True
                            file_analysis['segments'] = len(segments)
                            print(f"      ✅ Extracted generic EDI with {len(segments)} segments")
                    
                    elif file_type == 'csv':
                        # Analyze CSV structure first
                        csv_analysis = csv_processor.analyze_csv_structure(file_path)
                        file_analysis['csv_analysis'] = csv_analysis
                        
                        # Determine CSV type based on content analysis
                        # Check carrier first since it's more specific
                        if 'carrier' in file_path.name.lower() or self._looks_like_carrier(csv_analysis):
                            result = self.process_csv_file(file_path, ['order_id', 'eta'])
                            if 'error' not in result:
                                analysis['data_types']['carrier'] = result['data']
                                file_analysis['processed'] = True
                                file_analysis['rows'] = result['row_count']
                                print(f"      ✅ Processed Carrier CSV with {result['row_count']} rows")
                            else:
                                file_analysis['error'] = result['error']
                        elif 'erp' in file_path.name.lower() or self._looks_like_erp(csv_analysis):
                            result = self.process_csv_file(file_path, ['order_id'])
                            if 'error' not in result:
                                analysis['data_types']['erp'] = result['data']
                                file_analysis['processed'] = True
                                file_analysis['rows'] = result['row_count']
                                print(f"      ✅ Processed ERP CSV with {result['row_count']} rows")
                            else:
                                file_analysis['error'] = result['error']
                        else:
                            # Generic CSV processing
                            result = self.process_csv_file(file_path)
                            if 'error' not in result:
                                file_analysis['processed'] = True
                                file_analysis['rows'] = result['row_count']
                                print(f"      ✅ Processed generic CSV with {result['row_count']} rows")
                            else:
                                file_analysis['error'] = result['error']
                    
                    elif file_type == 'html_edi':
                        # Extract EDI content directly from HTML with EDI content
                        if '850' in file_path.name.lower() or 'po' in file_path.name.lower():
                            segments = self.extract_edi_from_html(file_path)
                            analysis['data_types']['edi_850'] = segments
                            file_analysis['processed'] = True
                            file_analysis['segments'] = len(segments)
                            print(f"      ✅ Extracted EDI 850 from HTML with {len(segments)} segments")
                        elif '856' in file_path.name.lower() or 'asn' in file_path.name.lower():
                            segments = self.extract_edi_from_html(file_path)
                            analysis['data_types']['edi_856'] = segments
                            file_analysis['processed'] = True
                            file_analysis['segments'] = len(segments)
                            print(f"      ✅ Extracted EDI 856 from HTML with {len(segments)} segments")
                        else:
                            # Generic EDI processing from HTML
                            segments = self.extract_edi_from_html(file_path)
                            file_analysis['processed'] = True
                            file_analysis['segments'] = len(segments)
                            print(f"      ✅ Extracted generic EDI from HTML with {len(segments)} segments")
                    
                    elif file_type == 'html':
                        # Extract EDI from HTML
                        from extract_edi import extract_edi_from_html
                        edi_filename = file_path.name.replace('.html', '_raw.edi')
                        edi_path = file_path.parent / edi_filename
                        
                        if extract_edi_from_html(file_path, edi_path):
                            file_analysis['processed'] = True
                            file_analysis['extracted_edi'] = str(edi_path)
                            print(f"      ✅ Extracted EDI from HTML to {edi_filename}")
                        else:
                            file_analysis['error'] = "Failed to extract EDI from HTML"
                    
                    if file_analysis['processed']:
                        analysis['summary']['processed_files'] += 1
                    else:
                        analysis['summary']['errors'] += 1
                        
                except Exception as e:
                    file_analysis['error'] = str(e)
                    analysis['summary']['errors'] += 1
                    print(f"      ❌ Error processing {file_path.name}: {e}")
                
                analysis['files'][file_path.name] = file_analysis
        
        return analysis
    
    def _looks_like_erp(self, csv_analysis: Dict[str, Any]) -> bool:
        """Determine if a CSV looks like ERP data based on column analysis."""
        if 'column_analysis' not in csv_analysis:
            return False
        
        erp_indicators = ['order_id', 'customer', 'amount', 'date', 'product']
        detected_types = set()
        
        for col_info in csv_analysis['column_analysis'].values():
            if 'detected_type' in col_info:
                detected_types.add(col_info['detected_type'])
        
        # If we have at least 2 ERP indicators, it's likely ERP data
        return len(detected_types.intersection(set(erp_indicators))) >= 2
    
    def _looks_like_carrier(self, csv_analysis: Dict[str, Any]) -> bool:
        """Determine if a CSV looks like carrier data based on column analysis."""
        if 'column_analysis' not in csv_analysis:
            return False
        
        carrier_indicators = ['order_id', 'eta', 'delivery', 'shipping']
        detected_types = set()
        
        for col_info in csv_analysis['column_analysis'].values():
            if 'detected_type' in col_info:
                detected_types.add(col_info['detected_type'])
        
        # If we have order_id and eta, it's likely carrier data
        return 'order_id' in detected_types and 'eta' in detected_types

def auto_detect_data_directory() -> Optional[Path]:
    """Automatically detect which data directory to use."""
    base_dir = Path(__file__).resolve().parent
    
    # Priority order: data_sample_org first, then sample_data
    data_dirs = [
        base_dir / "data_sample_org",
        base_dir / "sample_data"
    ]
    
    for data_dir in data_dirs:
        if data_dir.exists() and data_dir.is_dir():
            print(f"🎯 Auto-detected data directory: {data_dir}")
            return data_dir
    
    return None

def process_uploaded_files(upload_dir: Path) -> Dict[str, Any]:
    """Process files from an upload directory."""
    if not upload_dir.exists():
        return {"error": f"Upload directory not found: {upload_dir}"}
    
    data_files = list(upload_dir.glob("*"))
    if not data_files:
        return {"error": "No files found in upload directory"}
    
    processor = DynamicDataProcessor()
    return processor.analyze_data_files(data_files)

def main():
    """Main function with flexible data processing."""
    
    print("🚀 Unified AgentOps - Dynamic Data Processing")
    print("=" * 50)
    
    # Check command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == "--upload" and len(sys.argv) > 2:
            # Process uploaded files
            upload_dir = Path(sys.argv[2])
            print(f"📁 Processing uploaded files from: {upload_dir}")
            
            analysis = process_uploaded_files(upload_dir)
            if "error" in analysis:
                print(f"❌ {analysis['error']}")
                sys.exit(1)
            
            # Continue with AgentOps processing
            data_types = analysis['data_types']
            data_dir = upload_dir  # Set data_dir for upload path
        else:
            print("Usage: python3 main.py [--upload <upload_directory>]")
            sys.exit(1)
    else:
        # Auto-detect data directory
        data_dir = auto_detect_data_directory()
        
        if not data_dir:
            print("❌ No data directory found!")
            print("Please ensure either 'sample_data' or 'data_sample_org' directory exists.")
            print("Or use: python3 main.py --upload <directory>")
            sys.exit(1)
        
        print(f"📁 Using data directory: {data_dir}")
        
        # Process data files
        processor = DynamicDataProcessor()
        data_files = list(data_dir.glob("*"))
        analysis = processor.analyze_data_files(data_files)
        data_types = analysis['data_types']
    
    # Check if we have enough data to proceed
    required_data = ['edi_850', 'edi_856', 'erp', 'carrier']
    missing_data = [key for key in required_data if data_types[key] is None]
    
    if missing_data:
        print(f"\n⚠️  Missing data: {', '.join(missing_data)}")
        print("Some functionality may be limited.")
    
    # Initialize AgentOps
    print(f"\n🔧 Initializing AgentOps...")
    try:
        base_dir = Path(__file__).resolve().parent
        
        # Check if we have parsed data from the processor
        if all(analysis['data_types'].values()):
            # Convert CSV processor output to AgentOps expected format
            # ERP data: convert list of dicts to dict keyed by order_id
            erp_data = {}
            if analysis['data_types']['erp']:
                for row in analysis['data_types']['erp']:
                    order_id = row.get('po_number', row.get('order_id', ''))
                    if order_id:
                        erp_data[order_id] = row
            
            # Carrier data: convert list of dicts to dict keyed by order_id
            carrier_data = {}
            if analysis['data_types']['carrier']:
                for row in analysis['data_types']['carrier']:
                    order_id = row.get('po_number', row.get('order_id', ''))
                    eta = row.get('eta', '')
                    if order_id and eta:
                        carrier_data[order_id] = eta
            
            parsed_data = {
                'edi_850': analysis['data_types']['edi_850'],
                'edi_856': analysis['data_types']['edi_856'],
                'erp': erp_data,
                'carrier': carrier_data
            }
            agent = AgentOps(base_dir, data_dir_name=data_dir.name, parsed_data=parsed_data)
            print("✅ AgentOps initialized with parsed data!")
        else:
            # Fall back to file-based processing
            agent = AgentOps(base_dir, data_dir_name=data_dir.name)
            print("✅ AgentOps initialized with file paths!")
            
    except Exception as e:
        print(f"❌ Failed to initialize AgentOps: {e}")
        sys.exit(1)
    
    # Run the analysis
    print(f"\n🚀 Running AgentOps analysis...")
    try:
        com_json, rca_json, spans = agent.run()
        print("✅ Analysis completed successfully!")
        
        # Display results summary
        print(f"\n📊 Analysis Results:")
        print(f"   📦 Order ID: {com_json.get('order_id', {}).get('value', 'N/A')}")
        print(f"   🚨 Incidents: {1 if rca_json.get('status') != 'no_incident' else 0}")
        print(f"   ⚙️  Processing Steps: {len(spans)}")
        print(f"   🎨 Artifacts Generated: {'Yes' if len(spans) > 0 else 'No'}")
        
        # Show incident details if any
        if rca_json.get('status') != 'no_incident':
            print(f"\n🚨 Incident Details:")
            print(f"   - Problem: {rca_json.get('problem_type', 'Unknown')}")
            print(f"   - Status: {rca_json.get('status', 'Unknown')}")
        
        # Store results in Supabase if storage is available
        if STORAGE_AVAILABLE:
            print(f"\n💾 Checking Supabase storage availability...")
            storage_integration = FastAPIStorageIntegration()
            
            if storage_integration.is_available():
                print(f"✅ Supabase storage available - storing results...")
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
                print("⚠️  Supabase storage not available")
                print("   Artifacts are only stored locally in the artifacts/ directory")
                print("   To enable Supabase storage, set SUPABASE_URL and SUPABASE_KEY environment variables")
        else:
            print("\n⚠️  Supabase storage integration not available")
            print("   Artifacts are only stored locally in the artifacts/ directory")
        
        print(f"\n🎉 AgentOps analysis complete!")
        
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
