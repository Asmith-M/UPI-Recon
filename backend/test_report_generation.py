"""
Test script to verify all report generation functionality
"""
import os
import json
import pandas as pd
from datetime import datetime
from recon_engine import ReconciliationEngine
from settlement_engine import SettlementEngine
from config import OUTPUT_DIR

def test_report_generation():
    """Test comprehensive report generation"""
    print("=" * 80)
    print("TESTING REPORT GENERATION")
    print("=" * 80)
    
    # Create test data
    test_data = {
        'RRN001': {
            'cbs': {'amount': 1000, 'date': '2025-01-10', 'dr_cr': 'C', 'rc': '00', 'tran_type': 'INWARD'},
            'switch': {'amount': 1000, 'date': '2025-01-10', 'dr_cr': 'C', 'rc': '00', 'tran_type': 'INWARD'},
            'npci': {'amount': 1000, 'date': '2025-01-10', 'dr_cr': 'C', 'rc': '00', 'tran_type': 'INWARD'},
            'status': 'MATCHED'
        },
        'RRN002': {
            'cbs': {'amount': 2000, 'date': '2025-01-09', 'dr_cr': 'D', 'rc': '00', 'tran_type': 'OUTWARD'},
            'switch': {'amount': 2000, 'date': '2025-01-09', 'dr_cr': 'D', 'rc': '00', 'tran_type': 'OUTWARD'},
            'npci': None,
            'status': 'PARTIAL_MATCH'
        },
        'RRN003': {
            'cbs': None,
            'switch': {'amount': 500, 'date': '2025-01-08', 'dr_cr': 'C', 'rc': '00', 'tran_type': 'INWARD'},
            'npci': None,
            'status': 'ORPHAN'
        },
        'RRN004': {
            'cbs': {'amount': 1500, 'date': '2025-01-07', 'dr_cr': 'C', 'rc': 'RB', 'tran_type': 'INWARD'},
            'switch': {'amount': 1500, 'date': '2025-01-07', 'dr_cr': 'C', 'rc': 'RB', 'tran_type': 'INWARD'},
            'npci': {'amount': 1500, 'date': '2025-01-07', 'dr_cr': 'C', 'rc': 'RB', 'tran_type': 'INWARD'},
            'status': 'MATCHED',
            'tcc': 'TCC_102'
        },
        'RRN005': {
            'cbs': {'amount': 3000, 'date': '2025-01-06', 'dr_cr': 'D', 'rc': '00', 'tran_type': 'OUTWARD'},
            'switch': {'amount': 3000, 'date': '2025-01-06', 'dr_cr': 'D', 'rc': '00', 'tran_type': 'OUTWARD'},
            'npci': None,
            'status': 'HANGING',
            'hanging_reason': 'CBS and SWITCH present, NPCI missing'
        }
    }
    
    # Initialize engine
    engine = ReconciliationEngine(OUTPUT_DIR)
    run_id = f"TEST_RUN_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    run_folder = os.path.join(OUTPUT_DIR, run_id)
    os.makedirs(run_folder, exist_ok=True)
    
    print(f"\n✓ Created test run: {run_id}")
    print(f"✓ Run folder: {run_folder}")
    
    # Test 1: Generate matched reports
    print("\n" + "=" * 80)
    print("TEST 1: Generating Matched Transaction Reports")
    print("=" * 80)
    try:
        engine.generate_report(test_data, run_folder, run_id)
        reports_dir = os.path.join(run_folder, 'reports')
        if os.path.exists(reports_dir):
            files = os.listdir(reports_dir)
            print(f"✓ Generated {len(files)} report files:")
            for f in sorted(files):
                file_path = os.path.join(reports_dir, f)
                size = os.path.getsize(file_path)
                print(f"  - {f} ({size} bytes)")
        else:
            print("✗ Reports directory not created")
    except Exception as e:
        print(f"✗ Error generating matched reports: {e}")
    
    # Test 2: Generate unmatched ageing reports
    print("\n" + "=" * 80)
    print("TEST 2: Generating Unmatched Ageing Reports")
    print("=" * 80)
    try:
        engine.generate_unmatched_ageing(test_data, run_folder, run_id)
        reports_dir = os.path.join(run_folder, 'reports')
        ageing_files = [f for f in os.listdir(reports_dir) if 'Ageing' in f or 'ageing' in f]
        print(f"✓ Generated {len(ageing_files)} ageing report files:")
        for f in sorted(ageing_files):
            file_path = os.path.join(reports_dir, f)
            size = os.path.getsize(file_path)
            print(f"  - {f} ({size} bytes)")
            # Show sample data
            df = pd.read_csv(file_path)
            print(f"    Rows: {len(df)}, Columns: {list(df.columns)}")
    except Exception as e:
        print(f"✗ Error generating ageing reports: {e}")
    
    # Test 3: Generate hanging reports
    print("\n" + "=" * 80)
    print("TEST 3: Generating Hanging Transaction Reports")
    print("=" * 80)
    try:
        engine.generate_hanging_reports(test_data, run_folder, run_id)
        reports_dir = os.path.join(run_folder, 'reports')
        hanging_files = [f for f in os.listdir(reports_dir) if 'Hanging' in f or 'hanging' in f]
        print(f"✓ Generated {len(hanging_files)} hanging report files:")
        for f in sorted(hanging_files):
            file_path = os.path.join(reports_dir, f)
            size = os.path.getsize(file_path)
            print(f"  - {f} ({size} bytes)")
            # Show sample data
            df = pd.read_csv(file_path)
            print(f"    Rows: {len(df)}, Columns: {list(df.columns)}")
    except Exception as e:
        print(f"✗ Error generating hanging reports: {e}")
    
    # Test 4: Generate TTUM files
    print("\n" + "=" * 80)
    print("TEST 4: Generating TTUM Files")
    print("=" * 80)
    try:
        settlement_engine = SettlementEngine(OUTPUT_DIR)
        ttum_files = settlement_engine.generate_ttum_files(test_data, run_folder)
        print(f"✓ Generated {len(ttum_files)} TTUM files:")
        for category, path in ttum_files.items():
            if os.path.exists(path):
                size = os.path.getsize(path)
                print(f"  - {category}: {os.path.basename(path)} ({size} bytes)")
                # Show sample data
                if path.endswith('.csv'):
                    df = pd.read_csv(path)
                    print(f"    Rows: {len(df)}, Columns: {len(df.columns)}")
    except Exception as e:
        print(f"✗ Error generating TTUM files: {e}")
    
    # Test 5: Verify all reports exist
    print("\n" + "=" * 80)
    print("TEST 5: Verifying All Generated Reports")
    print("=" * 80)
    reports_dir = os.path.join(run_folder, 'reports')
    ttum_dir = os.path.join(run_folder, 'ttum')
    
    expected_reports = {
        'reports': [
            'GL_vs_Switch_Inward.csv',
            'GL_vs_Switch_Outward.csv',
            'Switch_vs_NPCI_Inward.csv',
            'Switch_vs_NPCI_Outward.csv',
            'GL_vs_NPCI_Inward.csv',
            'GL_vs_NPCI_Outward.csv',
            'Unmatched_Inward_Ageing.csv',
            'Unmatched_Outward_Ageing.csv',
            'Hanging_Inward.csv',
            'Hanging_Outward.csv',
        ],
        'ttum': [
            'drc.csv',
            'rrc.csv',
            'tcc.csv',
            'ret.csv',
            'refund.csv',
            'recovery.csv',
        ]
    }
    
    print("\nExpected Reports in /reports:")
    for report in expected_reports['reports']:
        path = os.path.join(reports_dir, report)
        if os.path.exists(path):
            size = os.path.getsize(path)
            print(f"  ✓ {report} ({size} bytes)")
        else:
            print(f"  ✗ {report} (NOT FOUND)")
    
    print("\nExpected TTUM Files in /ttum:")
    for report in expected_reports['ttum']:
        # Check in cycle subdirectory
        cycle_dir = os.path.join(ttum_dir, 'cycle_1C')
        path = os.path.join(cycle_dir, report)
        if os.path.exists(path):
            size = os.path.getsize(path)
            print(f"  ✓ {report} ({size} bytes)")
        else:
            print(f"  ✗ {report} (NOT FOUND)")
    
    # Test 6: Summary statistics
    print("\n" + "=" * 80)
    print("TEST 6: Report Summary Statistics")
    print("=" * 80)
    
    total_files = 0
    total_size = 0
    
    for root, dirs, files in os.walk(run_folder):
        for file in files:
            if file.endswith(('.csv', '.json', '.xlsx')):
                file_path = os.path.join(root, file)
                size = os.path.getsize(file_path)
                total_files += 1
                total_size += size
    
    print(f"✓ Total report files generated: {total_files}")
    print(f"✓ Total size: {total_size / 1024:.2f} KB")
    print(f"✓ Run folder: {run_folder}")
    
    print("\n" + "=" * 80)
    print("REPORT GENERATION TEST COMPLETED")
    print("=" * 80)
    
    return run_id, run_folder

if __name__ == "__main__":
    run_id, run_folder = test_report_generation()
    print(f"\nTest run ID: {run_id}")
    print(f"Test run folder: {run_folder}")
