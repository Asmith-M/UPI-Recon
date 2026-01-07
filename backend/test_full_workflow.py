#!/usr/bin/env python3
"""
Full workflow test script for UPI Reconciliation System.
This script:
1. Generates sample data (if not exists)
2. Uploads files to the system
3. Runs reconciliation
4. Generates reports
5. Tests report downloads

Usage: python test_full_workflow.py
"""

import os
import json
import time
from pathlib import Path
from datetime import datetime

# Import system components
from file_handler import FileHandler
from recon_engine import ReconciliationEngine
from upi_recon_engine import UPIReconciliationEngine
from config import UPLOAD_DIR, OUTPUT_DIR

def main():
    print("🚀 Starting UPI Reconciliation Full Workflow Test")
    print("=" * 60)

    # Initialize components
    file_handler = FileHandler()
    recon_engine = ReconciliationEngine(output_dir=OUTPUT_DIR)
    upi_recon_engine = UPIReconciliationEngine()

    # Step 1: Check for sample data files
    print("\n📁 Step 1: Checking sample data files...")
    sample_dir = "bank_recon_files"

    required_files = {
        'cbs_inward': '1_CBS_Inward.xlsx',
        'cbs_outward': '2_CBS_Outward.xlsx',
        'switch': '3_Switch.xlsx',
        'npci_inward': '4_NPCI_Inward.xlsx',
        'npci_outward': '5_NPCI_Outward.xlsx',
        'ntsl': '6_NTSL.xlsx',
        'adjustment': '7_Internal_Adjustments.xlsx'
    }

    missing_files = []
    for key, filename in required_files.items():
        filepath = os.path.join(sample_dir, filename)
        if not os.path.exists(filepath):
            missing_files.append(filename)

    if missing_files:
        print(f"❌ Missing sample files: {missing_files}")
        print("🔧 Generating sample data first...")
        os.system("python data_gen.py")
        time.sleep(2)  # Wait for generation

        # Check again
        still_missing = []
        for key, filename in required_files.items():
            filepath = os.path.join(sample_dir, filename)
            if not os.path.exists(filepath):
                still_missing.append(filename)

        if still_missing:
            print(f"❌ Failed to generate sample files: {still_missing}")
            return False

    print("✅ All sample files found")

    # Step 2: Upload files
    print("\n📤 Step 2: Uploading files...")
    run_id = f"RUN_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    # Load file contents
    uploaded_files_content = {}
    for key, filename in required_files.items():
        filepath = os.path.join(sample_dir, filename)
        try:
            with open(filepath, 'rb') as f:
                content = f.read()
                uploaded_files_content[filename] = content
                print(f"  📄 Loaded {filename} ({len(content)} bytes)")
        except Exception as e:
            print(f"  ❌ Failed to load {filename}: {e}")
            return False

    # Save uploaded files
    try:
        run_folder = file_handler.save_uploaded_files(
            uploaded_files_content,
            run_id,
            cycle="1C",
            direction="INWARD",
            run_date=datetime.now().strftime("%Y-%m-%d")
        )
        print(f"✅ Files uploaded successfully to {run_folder}")
    except Exception as e:
        print(f"❌ File upload failed: {e}")
        return False

    # Step 3: Load and validate dataframes
    print("\n🔍 Step 3: Loading and validating data...")
    try:
        dataframes = file_handler.load_files_for_recon(run_folder)
        print(f"✅ Loaded {len(dataframes)} dataframes")

        # Show summary of each dataframe
        for i, df in enumerate(dataframes):
            source = df['Source'].iloc[0] if len(df) > 0 else 'UNKNOWN'
            print(f"  📊 DataFrame {i+1}: {source} - {len(df)} records")

    except Exception as e:
        print(f"❌ Data loading failed: {e}")
        return False

    # Step 4: Run reconciliation
    print("\n⚙️ Step 4: Running reconciliation...")
    try:
        # Detect if this is UPI reconciliation
        is_upi_run = any('UPI_Tran_ID' in df.columns for df in dataframes)
        print(f"  🎯 Detected {'UPI' if is_upi_run else 'Legacy'} reconciliation format")

        if is_upi_run:
            # Extract UPI-specific dataframes
            cbs_df = pd.DataFrame()
            switch_df = pd.DataFrame()
            npci_df = pd.DataFrame()

            for df in dataframes:
                source = str(df['Source'].iloc[0]).upper() if len(df) > 0 else ''
                if source == 'CBS':
                    cbs_df = pd.concat([cbs_df, df], ignore_index=True)
                elif source == 'SWITCH':
                    switch_df = pd.concat([switch_df, df], ignore_index=True)
                elif source == 'NPCI':
                    npci_df = pd.concat([npci_df, df], ignore_index=True)

            print(f"  📊 CBS: {len(cbs_df)} records, Switch: {len(switch_df)} records, NPCI: {len(npci_df)} records")

            # Run UPI reconciliation
            results = upi_recon_engine.perform_upi_reconciliation(cbs_df, switch_df, npci_df, run_id)
            print("✅ UPI reconciliation completed")

            # Save results
            output_run_dir = os.path.join(OUTPUT_DIR, run_id)
            os.makedirs(output_run_dir, exist_ok=True)
            recon_output_path = os.path.join(output_run_dir, "recon_output.json")

            with open(recon_output_path, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, default=str)
            print(f"✅ Results saved to {recon_output_path}")

            # Generate reports
            try:
                recon_engine.generate_upi_report(results, output_run_dir, run_id=run_id)
                print("✅ UPI reports generated")
            except Exception as e:
                print(f"⚠️ UPI report generation failed: {e}")

        else:
            # Legacy reconciliation
            results = recon_engine.reconcile(dataframes)
            print("✅ Legacy reconciliation completed")

            # Generate reports
            recon_engine.generate_report(results, run_folder, run_id=run_id)
            recon_engine.generate_adjustments_csv(results, run_folder)
            recon_engine.generate_unmatched_ageing(results, run_folder)
            print("✅ Legacy reports generated")

    except Exception as e:
        print(f"❌ Reconciliation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Step 5: Verify report generation
    print("\n📋 Step 5: Verifying report generation...")

    # Check output directory
    output_run_dir = os.path.join(OUTPUT_DIR, run_id)
    if os.path.exists(output_run_dir):
        print(f"✅ Output directory exists: {output_run_dir}")

        # List generated files
        generated_files = []
        for root, dirs, files in os.walk(output_run_dir):
            for file in files:
                rel_path = os.path.relpath(os.path.join(root, file), output_run_dir)
                generated_files.append(rel_path)

        if generated_files:
            print("📄 Generated files:")
            for file in sorted(generated_files):
                file_path = os.path.join(output_run_dir, file)
                size = os.path.getsize(file_path)
                print(f"  - {file} ({size} bytes)")
        else:
            print("⚠️ No files generated in output directory")
    else:
        print(f"❌ Output directory not found: {output_run_dir}")

    # Step 6: Test report availability
    print("\n🧪 Step 6: Testing report availability...")

    # Import reporting functions
    try:
        from reporting import get_ttum_files

        # Check TTUM files
        ttum_files = get_ttum_files(run_id)
        if ttum_files:
            print(f"✅ TTUM files available: {len(ttum_files)} files")
            for file_path in ttum_files[:3]:  # Show first 3
                print(f"  - {os.path.basename(file_path)}")
        else:
            print("⚠️ No TTUM files found")

        # Check CSV format
        ttum_csv = get_ttum_files(run_id, format='csv')
        if ttum_csv:
            print(f"✅ TTUM CSV files available: {len(ttum_csv)} files")

        # Check XLSX format
        ttum_xlsx = get_ttum_files(run_id, format='xlsx')
        if ttum_xlsx:
            print(f"✅ TTUM XLSX files available: {len(ttum_xlsx)} files")

    except Exception as e:
        print(f"⚠️ Report availability check failed: {e}")

    print("\n" + "=" * 60)
    print("🎉 Full workflow test completed!")
    print(f"📝 Run ID: {run_id}")
    print(f"📂 Output directory: {output_run_dir}")
    print("\n💡 You can now test report downloads via the API endpoints:")
    print(f"   - GET /api/v1/reports/ttum?run_id={run_id}")
    print(f"   - GET /api/v1/reports/ttum/csv?run_id={run_id}")
    print(f"   - GET /api/v1/reports/ttum/xlsx?run_id={run_id}")
    print(f"   - GET /api/v1/reports/matched?run_id={run_id}")
    print(f"   - GET /api/v1/reports/unmatched?run_id={run_id}")
    print(f"   - GET /api/v1/summary?run_id={run_id}")

    return True

if __name__ == "__main__":
    import pandas as pd  # Import here to avoid issues
    success = main()
    exit(0 if success else 1)
