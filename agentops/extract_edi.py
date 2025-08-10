#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unified EDI Utility for AgentOps

This script provides EDI content extraction from HTML documentation files,
data validation, and testing functionality for the AgentOps system.
"""

import re
import os
import json
import sys
from pathlib import Path

def extract_edi_from_html(html_file_path, output_file_path):
    """Extract EDI content from HTML file and save to output file."""
    
    print(f"📄 Processing {html_file_path}...")
    
    try:
        with open(html_file_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        # Find the EDI content in the <pre> tags
        pre_match = re.search(r'<pre[^>]*>(.*?)</pre>', html_content, re.DOTALL)
        
        if pre_match:
            edi_content = pre_match.group(1)
            
            # Clean up the EDI content
            edi_content = edi_content.strip()
            
            # Write to output file
            with open(output_file_path, 'w', encoding='utf-8') as f:
                f.write(edi_content)
            
            print(f"✅ Extracted EDI content to {output_file_path}")
            print(f"   Content length: {len(edi_content)} characters")
            
            # Show first few lines
            lines = edi_content.split('\n')
            print(f"   First line: {lines[0]}")
            if len(lines) > 1:
                print(f"   Last line: {lines[-1]}")
            
            return True
        else:
            print(f"❌ No EDI content found in {html_file_path}")
            return False
            
    except Exception as e:
        print(f"❌ Error processing {html_file_path}: {e}")
        return False

def validate_data_directory(data_dir: Path) -> bool:
    """Validate that a data directory contains all required files."""
    print(f"🔍 Validating data directory: {data_dir}")
    
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
        if file_path.exists():
            size = file_path.stat().st_size
            print(f"   ✅ {file_name} ({size} bytes)")
        else:
            print(f"   ❌ {file_name} - MISSING")
            missing_files.append(file_name)
    
    if missing_files:
        print(f"\n❌ Missing required files: {', '.join(missing_files)}")
        print("Please ensure all required files are present.")
        return False
    
    print(f"\n✅ All required files found!")
    return True

def test_agentops_integration(base_dir: Path, data_dir_name: str = "temp_data") -> bool:
    """Test AgentOps integration with the specified data directory."""
    print(f"\n🔧 Testing AgentOps integration...")
    
    try:
        # Import AgentOps
        from agent_ops import AgentOps
        
        # Initialize AgentOps
        agent = AgentOps(base_dir, data_dir_name=data_dir_name)
        print("✅ AgentOps initialized successfully!")
        
        # Test basic functionality
        print("\n🔍 Testing basic functionality...")
        com_json, rca_json, spans = agent.run()
        
        print("✅ AgentOps analysis completed successfully!")
        print(f"📊 Order ID: {com_json.get('order_id', {}).get('value', 'N/A')}")
        print(f"📊 Incidents: {len([s for s in spans if 'incident' in s.tool.lower()])}")
        print(f"📊 Total spans: {len(spans)}")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Please ensure all required modules are available.")
        return False
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def extract_all_edi_files():
    """Extract EDI content from all HTML files in the current directory."""
    print("🔍 EDI Content Extractor")
    print("=" * 40)
    
    # Look for HTML files in the current directory
    html_files = [f for f in os.listdir('.') if f.endswith('.html')]
    
    if not html_files:
        print("❌ No HTML files found in current directory")
        return False
    
    success_count = 0
    
    for html_file in html_files:
        edi_file = html_file.replace('.html', '_raw.edi')
        if extract_edi_from_html(html_file, edi_file):
            success_count += 1
    
    print("\n" + "=" * 40)
    print(f"🎉 Extraction complete! {success_count}/{len(html_files)} files processed successfully.")
    
    if success_count > 0:
        print("\n📁 Files created:")
        for html_file in html_files:
            edi_file = html_file.replace('.html', '_raw.edi')
            if os.path.exists(edi_file):
                print(f"   ✅ {edi_file}")
        
        print("\n🚀 EDI files extracted successfully!")
    
    return success_count > 0

def run_comprehensive_test():
    """Run a comprehensive test of the AgentOps system."""
    print("🧪 Comprehensive AgentOps System Test")
    print("=" * 60)
    
    # Get the current directory
    base_dir = Path(__file__).resolve().parent
    print(f"📁 Base directory: {base_dir}")
    
    # Step 1: Extract EDI files if needed
    print("\n📋 Step 1: EDI File Extraction")
    print("-" * 40)
    if not extract_all_edi_files():
        print("⚠️  EDI extraction had issues, but continuing...")
    
    # Step 2: Test AgentOps integration with minimal data
    print("\n📋 Step 2: AgentOps Integration Test")
    print("-" * 40)
    if not test_agentops_integration(base_dir, "temp_data"):
        print("❌ AgentOps integration test failed!")
        return False
    
    print("\n" + "=" * 60)
    print("🎉 All tests passed! AgentOps system is ready.")
    print("=" * 60)
    
    return True

def main():
    """Main function with multiple operation modes."""
    import argparse
    
    parser = argparse.ArgumentParser(description="AgentOps EDI Utility")
    parser.add_argument("--extract", action="store_true", help="Extract EDI files from HTML")
    parser.add_argument("--validate", action="store_true", help="Validate data directory")
    parser.add_argument("--test", action="store_true", help="Run comprehensive system test")
    parser.add_argument("--all", action="store_true", help="Run all operations")
    
    args = parser.parse_args()
    
    # If no arguments provided, run comprehensive test
    if not any([args.extract, args.validate, args.test, args.all]):
        args.all = True
    
    if args.all or args.extract:
        print("📋 Running EDI extraction...")
        extract_all_edi_files()
    
    if args.all or args.validate:
        print("\n📋 Running data validation...")
        base_dir = Path(__file__).resolve().parent
        data_dir = base_dir / "temp_data"
        validate_data_directory(data_dir)
    
    if args.all or args.test:
        print("\n📋 Running comprehensive test...")
        run_comprehensive_test()

if __name__ == "__main__":
    main()
