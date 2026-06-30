#!/usr/bin/env python
"""
Convert H&M Parquet files to CSV format
Run this script before setup_data.py
"""

import pandas as pd
from pathlib import Path
import sys

# Add parent directory to path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.config import RAW_DATA_DIR

def convert_parquet_to_csv():
    """Convert all parquet files in data/raw to CSV"""
    
    print("\n" + "="*60)
    print("H&M Dataset - Parquet to CSV Converter")
    print("="*60 + "\n")
    
    # Define expected parquet files
    parquet_files = {
        'articles': 'articles.parquet',
        'customers': 'customers.parquet',
        'transactions_train': 'transactions_train.parquet'
    }
    
    converted = []
    missing = []
    errors = []
    
    for name, filename in parquet_files.items():
        parquet_path = RAW_DATA_DIR / filename
        csv_path = RAW_DATA_DIR / f"{name}.csv"
        
        print(f"Processing {filename}...")
        
        if not parquet_path.exists():
            print(f"  ⚠️  File not found: {parquet_path}")
            missing.append(filename)
            continue
        
        try:
            # Read parquet file
            print(f"  📖 Reading parquet file...")
            df = pd.read_parquet(parquet_path)
            
            print(f"  📊 Loaded {len(df):,} rows, {len(df.columns)} columns")
            
            # Save as CSV
            print(f"  💾 Saving as CSV...")
            df.to_csv(csv_path, index=False)
            
            # Get file sizes
            parquet_size = parquet_path.stat().st_size / (1024 * 1024)  # MB
            csv_size = csv_path.stat().st_size / (1024 * 1024)  # MB
            
            print(f"  ✅ Converted successfully!")
            print(f"     Parquet: {parquet_size:.2f} MB → CSV: {csv_size:.2f} MB")
            print(f"     Saved to: {csv_path.name}\n")
            
            converted.append(name)
            
        except Exception as e:
            print(f"  ❌ Error converting {filename}: {e}\n")
            errors.append((filename, str(e)))
    
    # Summary
    print("\n" + "="*60)
    print("Conversion Summary")
    print("="*60 + "\n")
    
    if converted:
        print(f"✅ Successfully converted {len(converted)} file(s):")
        for name in converted:
            print(f"   • {name}.parquet → {name}.csv")
    
    if missing:
        print(f"\n⚠️  Missing {len(missing)} file(s):")
        for filename in missing:
            print(f"   • {filename}")
        print("\nPlease ensure all parquet files are in data/raw/ directory")
    
    if errors:
        print(f"\n❌ Failed to convert {len(errors)} file(s):")
        for filename, error in errors:
            print(f"   • {filename}: {error}")
    
    print("\n" + "="*60)
    
    if converted and not errors:
        print("✨ All files converted successfully!")
        print("\nNext steps:")
        print("1. Run: python scripts/setup_data.py")
        print("2. Then: python run.py")
    elif missing:
        print("⚠️  Please add the missing parquet files and run again")
    
    print("="*60 + "\n")

if __name__ == "__main__":
    convert_parquet_to_csv()