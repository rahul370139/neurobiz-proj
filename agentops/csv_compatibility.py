#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Generic CSV Processor for AgentOps

This module provides flexible CSV processing that can handle any column format
dynamically, making it suitable for frontend uploads with varying data structures.
"""

import csv
import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

class GenericCSVProcessor:
    """Generic CSV processor that can handle any column format dynamically."""
    
    def __init__(self):
        # Common column name variations for different data types
        self.column_mappings = {
            'order_id': ['order_id', 'po_number', 'po_num', 'purchase_order', 'order_number', 'id'],
            'eta': ['eta', 'estimated_time', 'delivery_time', 'arrival_time', 'expected_time'],
            'customer': ['customer', 'customer_name', 'client', 'client_name', 'buyer'],
            'amount': ['amount', 'total', 'value', 'price', 'cost', 'order_value'],
            'status': ['status', 'state', 'condition', 'order_status'],
            'date': ['date', 'order_date', 'created_date', 'timestamp'],
            'quantity': ['quantity', 'qty', 'amount', 'count'],
            'product': ['product', 'item', 'sku', 'product_name', 'description']
        }
    
    def detect_column_type(self, column_name: str) -> Optional[str]:
        """Detect what type of data a column contains based on its name."""
        column_lower = column_name.lower().strip()
        
        for data_type, variations in self.column_mappings.items():
            if any(var in column_lower for var in variations):
                return data_type
        
        return None
    
    def normalize_column_names(self, fieldnames: List[str]) -> Dict[str, str]:
        """Create a mapping from original column names to normalized types."""
        mapping = {}
        for col in fieldnames:
            if col:
                normalized_type = self.detect_column_type(col)
                if normalized_type:
                    mapping[col] = normalized_type
                else:
                    # Keep original name for unknown columns
                    mapping[col] = col
        return mapping
    
    def parse_csv_generic(self, file_path: Path, expected_types: List[str] = None) -> Dict[str, Any]:
        """
        Parse any CSV file and return structured data with column type detection.
        
        Args:
            file_path: Path to the CSV file
            expected_types: List of expected data types (e.g., ['order_id', 'eta'])
        
        Returns:
            Dictionary with parsed data and metadata
        """
        try:
            with file_path.open("r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                fieldnames = reader.fieldnames or []
                
                if not fieldnames:
                    raise ValueError("No field names found in CSV")
                
                # Detect column types
                column_mapping = self.normalize_column_names(fieldnames)
                
                # Parse rows
                rows = []
                for row in reader:
                    if any(row.values()):  # Skip empty rows
                        normalized_row = {}
                        for key, value in row.items():
                            normalized_row[key] = value.strip() if value else ""
                        rows.append(normalized_row)
                
                # Validate required columns if expected_types provided
                if expected_types:
                    missing_types = []
                    for expected_type in expected_types:
                        if not any(expected_type in col_type for col_type in column_mapping.values()):
                            missing_types.append(expected_type)
                    
                    if missing_types:
                        raise ValueError(f"Missing required column types: {missing_types}")
                
                return {
                    "data": rows,
                    "column_mapping": column_mapping,
                    "fieldnames": fieldnames,
                    "row_count": len(rows),
                    "file_path": str(file_path)
                }
                
        except Exception as e:
            raise ValueError(f"Error parsing CSV {file_path}: {e}")
    
    def parse_erp_csv(self, file_path: Path) -> Dict[str, Dict[str, str]]:
        """
        Parse ERP CSV with flexible column detection.
        
        Returns:
            Dictionary mapping order_id to ERP data
        """
        result = self.parse_csv_generic(file_path, ['order_id'])
        
        # Find the order_id column
        order_id_col = None
        for col, col_type in result["column_mapping"].items():
            if col_type == 'order_id':
                order_id_col = col
                break
        
        if not order_id_col:
            raise ValueError("No order_id column found in ERP CSV")
        
        # Convert to expected format
        erp_data = {}
        for row in result["data"]:
            if row.get(order_id_col):
                order_id = row[order_id_col]
                erp_data[order_id] = row
        
        return erp_data
    
    def parse_carrier_csv(self, file_path: Path) -> Dict[str, str]:
        """
        Parse carrier CSV with flexible column detection.
        
        Returns:
            Dictionary mapping order_id to ETA
        """
        result = self.parse_csv_generic(file_path, ['order_id', 'eta'])
        
        # Find the order_id and eta columns
        order_id_col = None
        eta_col = None
        
        for col, col_type in result["column_mapping"].items():
            if col_type == 'order_id':
                order_id_col = col
            elif col_type == 'eta':
                eta_col = col
        
        if not order_id_col or not eta_col:
            raise ValueError("Missing required columns: order_id and eta")
        
        # Convert to expected format
        carrier_data = {}
        for row in result["data"]:
            if row.get(order_id_col) and row.get(eta_col):
                order_id = row[order_id_col]
                eta = row[eta_col]
                carrier_data[order_id] = eta
        
        return carrier_data
    
    def analyze_csv_structure(self, file_path: Path) -> Dict[str, Any]:
        """
        Analyze CSV structure and provide insights about the data.
        
        Returns:
            Dictionary with analysis results
        """
        try:
            result = self.parse_csv_generic(file_path)
            
            # Analyze data types and patterns
            analysis = {
                "file_info": {
                    "path": str(file_path),
                    "size_bytes": file_path.stat().st_size,
                    "total_rows": result["row_count"],
                    "total_columns": len(result["fieldnames"])
                },
                "column_analysis": {},
                "data_quality": {
                    "empty_rows": 0,
                    "complete_rows": 0
                }
            }
            
            # Analyze each column
            for col in result["fieldnames"]:
                if col:
                    col_type = result["column_mapping"].get(col, "unknown")
                    sample_values = []
                    non_empty_count = 0
                    
                    for row in result["data"]:
                        value = row.get(col, "")
                        if value:
                            non_empty_count += 1
                            if len(sample_values) < 5:  # Keep first 5 non-empty values
                                sample_values.append(value)
                    
                    analysis["column_analysis"][col] = {
                        "detected_type": col_type,
                        "non_empty_count": non_empty_count,
                        "empty_count": result["row_count"] - non_empty_count,
                        "completeness_rate": non_empty_count / result["row_count"] if result["row_count"] > 0 else 0,
                        "sample_values": sample_values
                    }
            
            # Count complete vs incomplete rows
            for row in result["data"]:
                if all(row.values()):
                    analysis["data_quality"]["complete_rows"] += 1
                else:
                    analysis["data_quality"]["empty_rows"] += 1
            
            return analysis
            
        except Exception as e:
            return {"error": str(e), "file_path": str(file_path)}

# Create a global instance for easy access
csv_processor = GenericCSVProcessor()

# Backward compatibility functions
def parse_erp_csv_compatible(path: Path) -> Dict[str, Dict[str, str]]:
    """Backward compatibility function for existing code."""
    return csv_processor.parse_erp_csv(path)

def parse_carrier_csv_compatible(path: Path) -> Dict[str, str]:
    """Backward compatibility function for existing code."""
    return csv_processor.parse_carrier_csv(path)

def get_csv_column_mapping(file_path: Path) -> Dict[str, str]:
    """Backward compatibility function for existing code."""
    return csv_processor.analyze_csv_structure(file_path)
