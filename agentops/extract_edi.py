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

def test_agentops_integration(base_dir: Path, data_dir_name: str = "data_sample_org") -> bool:
    """Test AgentOps integration with the specified data directory."""
    print(f"\n🔧 Testing AgentOps integration...")
    
    try:
        # Import AgentOps
        from agent_ops import AgentOps
        
        # Initialize AgentOps
        agent = AgentOps(base_dir, data_dir_name=data_dir_name)
        print("✅ AgentOps initialized successfully!")
        
        # Test data parsing
        print("\n🔍 Testing data parsing...")
        data_dir = base_dir / data_dir_name
        
        # Test EDI parsing
        edi_850_path = data_dir / "po_850_raw.edi"
        edi_856_path = data_dir / "asn_856_raw.edi"
        
        from agent_ops import read_edi_file
        edi_850_segments = read_edi_file(edi_850_path)
        edi_856_segments = read_edi_file(edi_856_path)
        
        print(f"   ✅ EDI 850 parsed: {len(edi_850_segments)} segments")
        print(f"   ✅ EDI 856 parsed: {len(edi_856_segments)} segments")
        
        # Test CSV parsing with compatibility layer
        erp_path = data_dir / "erp_iway.csv"
        carrier_path = data_dir / "carrier_iway.csv"
        
        from csv_compatibility import parse_erp_csv_compatible, parse_carrier_csv_compatible
        erp_data = parse_erp_csv_compatible(erp_path)
        carrier_data = parse_carrier_csv_compatible(carrier_path)
        
        print(f"   ✅ ERP CSV parsed: {len(erp_data)} records")
        print(f"   ✅ Carrier CSV parsed: {len(carrier_data)} records")
        
        print("\n✅ All data parsing tests passed!")
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
    """Extract EDI content from all HTML files in data_sample_org."""
    print("🔍 EDI Content Extractor")
    print("=" * 40)
    
    # Define input and output file mappings
    file_mappings = [
        ("data_sample_org/po_850.edi", "data_sample_org/po_850_raw.edi"),
        ("data_sample_org/asn_856.edi", "data_sample_org/asn_856_raw.edi")
    ]
    
    success_count = 0
    
    for html_file, edi_file in file_mappings:
        if os.path.exists(html_file):
            if extract_edi_from_html(html_file, edi_file):
                success_count += 1
        else:
            print(f"❌ File not found: {html_file}")
    
    print("\n" + "=" * 40)
    print(f"🎉 Extraction complete! {success_count}/{len(file_mappings)} files processed successfully.")
    
    if success_count > 0:
        print("\n📁 Files created:")
        for _, edi_file in file_mappings:
            if os.path.exists(edi_file):
                print(f"   ✅ {edi_file}")
        
        print("\n🚀 You can now run AgentOps with the extracted EDI files!")
        print("   Run: python3 main.py")
    
    return success_count > 0

def run_comprehensive_test():
    """Run a comprehensive test of the AgentOps system."""
    print("🧪 Comprehensive AgentOps System Test")
    print("=" * 60)
    
    # Get the current directory
    base_dir = Path(__file__).resolve().parent
    data_dir = base_dir / "data_sample_org"
    
    print(f"📁 Base directory: {base_dir}")
    print(f"📁 Data directory: {data_dir}")
    
    # Step 1: Extract EDI files if needed
    print("\n📋 Step 1: EDI File Extraction")
    print("-" * 40)
    if not extract_all_edi_files():
        print("⚠️  EDI extraction had issues, but continuing...")
    
    # Step 2: Validate data directory
    print("\n📋 Step 2: Data Directory Validation")
    print("-" * 40)
    if not validate_data_directory(data_dir):
        print("❌ Data validation failed!")
        return False
    
    # Step 3: Test AgentOps integration
    print("\n📋 Step 3: AgentOps Integration Test")
    print("-" * 40)
    if not test_agentops_integration(base_dir):
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
        data_dir = base_dir / "data_sample_org"
        validate_data_directory(data_dir)
    
    if args.all or args.test:
        print("\n📋 Running comprehensive test...")
        run_comprehensive_test()

if __name__ == "__main__":
    main()
