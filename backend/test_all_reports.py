"""
Comprehensive test script to verify ALL report generation functionality
Tests every report type and validates output
"""
import os
import json
import pandas as pd
from datetime import datetime
from recon_engine import ReconciliationEngine
from settlement_engine import SettlementEngine
from config import OUTPUT_DIR

def create_comprehensive_test_data():
    """Create comprehensive test data covering all scenarios"""
    return {
        # Matched transactions
        'RRN001': {
            'cbs': {'amount': 1000, 'date': '2025-01-10', 'dr_cr': 'C', 'rc': '00', 'tran_type': 'INWARD'},
            'switch': {'amount': 1000, 'date': '2025-01-10', 'dr_cr': 'C', 'rc': '00', 'tran_type': 'INWARD'},
            'npci': {'amount': 1000, 'date': '2025-01-10', 'dr_cr': 'C', 'rc': '00', 'tran_type': 'INWARD'},
            'status': 'MATCHED'
        },
        'RRN002': {
            'cbs': {'amount': 2000, 'date': '2025-01-09', 'dr_cr': 'D', 'rc': '00', 'tran_type': 'OUTWARD'},
            'switch': {'amount': 2000, 'date': '2025-01-09', 'dr_cr': 'D', 'rc': '00', 'tran_type': 'OUTWARD'},
            'npci': {'amount': 2000, 'date': '2025-01-09', 'dr_cr': 'D', 'rc': '00', 'tran_type': 'OUTWARD'},
            'status': 'MATCHED'
        },
        # Partial matches
        'RRN003': {
            'cbs': {'amount': 3000, 'date': '2025-01-08', 'dr_cr': 'C', 'rc': '00', 'tran_type': 'INWARD'},
            'switch': {'amount': 3000, 'date': '2025-01-08', 'dr_cr': 'C', 'rc': '00', 'tran_type': 'INWARD'},
            'npci': None,
            'status': 'PARTIAL_MATCH'
        },
        'RRN004': {
            'cbs': {'amount': 4000, 'date': '2025-01-07', 'dr_cr': 'D', 'rc': '00', 'tran_type': 'OUTWARD'},
            'switch': None,
            'npci': {'amount': 4000, 'date': '2025-01-07', 'dr_cr': 'D', 'rc': '00', 'tran_type': 'OUTWARD'},
            'status': 'PARTIAL_MATCH'
        },
        # Orphans
        'RRN005': {
            'cbs': {'amount': 500, 'date': '2025-01-06', 'dr_cr': 'C', 'rc': '00', 'tran_type': 'INWARD'},
            'switch': None,
            'npci': None,
            'status': 'ORPHAN'
        },
        'RRN006': {
            'cbs': None,
            'switch': {'amount': 600, 'date': '2025-01-05', 'dr_cr': 'D', 'rc': '00', 'tran_type': 'OUTWARD'},
            'npci': None,
            'status': 'ORPHAN'
        },
        # Mismatches
        'RRN007': {
            'cbs': {'amount': 700, 'date': '2025-01-04', 'dr_cr': 'C', 'rc': '00', 'tran_type': 'INWARD'},
            'switch': {'amount': 800, 'date': '2025-01-04', 'dr_cr': 'C', 'rc': '00', 'tran_type': 'INWARD'},
            'npci': {'amount': 900, 'date': '2025-01-04', 'dr_cr': 'C', 'rc': '00', 'tran_type': 'INWARD'},
            'status': 'MISMATCH'
        },
        # TCC candidates
        'RRN008': {
            'cbs': {'amount': 1000, 'date': '2025-01-03', 'dr_cr': 'C', 'rc': '00', 'tran_type': 'INWARD'},
            'switch': {'amount': 1000, 'date': '2025-01-03', 'dr_cr': 'C', 'rc': '00', 'tran_type': 'INWARD'},
            'npci': {'amount': 1000, 'date': '2025-01-03', 'dr_cr': 'C', 'rc': 'RB', 'tran_type': 'INWARD'},
            'status': 'MATCHED',
            'tcc': 'TCC_102'
        },
        # Hanging transactions
        'RRN009': {
            'cbs': {'amount': 1100, 'date': '2025-01-02', 'dr_cr': 'C', 'rc': '00', 'tran_type': 'INWARD'},
            'switch': {'amount': 1100, 'date': '2025-01-02', 'dr_cr': 'C', 'rc': '00', 'tran_type': 'INWARD'},
            'npci': None,
            'status': 'HANGING',
            'hanging_reason': 'CBS and SWITCH present, NPCI missing'
        },
        'RRN010': {
            'cbs': {'amount': 1200, 'date': '2025-01-01', 'dr_cr': 'D', 'rc': '00', 'tran_type': 'OUTWARD'},
            'switch': {'amount': 1200, 'date': '2025-01-01', 'dr_cr': 'D', 'rc': '00', 'tran_type': 'OUTWARD'},
            'npci': None,
            'status': 'HANGING',
            'hanging_reason': 'CBS and SWITCH present, NPCI missing'
        },
        # Force matched
        'RRN011': {
            'cbs': {'amount': 1300, 'date': '2024-12-31', 'dr_cr': 'C', 'rc': '00', 'tran_type': 'INWARD'},
            'switch': {'amount': 1300, 'date': '2024-12-31', 'dr_cr': 'C', 'rc': '00', 'tran_type': 'INWARD'},
            'npci': {'amount': 1300, 'date': '2024-12-31', 'dr_cr': 'C', 'rc': '00', 'tran_type': 'INWARD'},
            'status': 'FORCE_MATCHED'
        }
    }

def test_all_reports():
    """Test all report generation functionality"""
    print("=" * 100)
    print("COMPREHENSIVE REPORT GENERATION TEST")
    print("=" * 100)

    # Create test data
    test_data = create_comprehensive_test_data()
    print(f"✓ Created test data with {len(test_data)} transactions")

    # Initialize engines
    engine = ReconciliationEngine(OUTPUT_DIR)
    settlement_engine = SettlementEngine(OUTPUT_DIR)

    run_id = f"COMPREHENSIVE_TEST_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    cycle_id = '1C'
    run_folder = os.path.join(OUTPUT_DIR, run_id)
    os.makedirs(run_folder, exist_ok=True)

    print(f"✓ Test run: {run_id}")
    print(f"✓ Cycle ID: {cycle_id}")
    print(f"✓ Run folder: {run_folder}")

    reports_generated = []
    errors = []

    # Test 1: Matched Transaction Reports
    print("\n" + "=" * 80)
    print("TEST 1: Matched Transaction Reports")
    print("=" * 80)
    try:
        engine.generate_report(test_data, run_folder, run_id, cycle_id)
        reports_dir = os.path.join(run_folder, 'reports')

        matched_reports = [
            'GL_vs_Switch_Inward.csv', 'GL_vs_Switch_Outward.csv',
            'Switch_vs_NPCI_Inward.csv', 'Switch_vs_NPCI_Outward.csv',
            'GL_vs_NPCI_Inward.csv', 'GL_vs_NPCI_Outward.csv'
        ]

        for report in matched_reports:
            path = os.path.join(reports_dir, report)
            if os.path.exists(path):
                df = pd.read_csv(path)
                size = os.path.getsize(path)
                print(f"✓ {report}: {len(df)} records ({size} bytes)")
                reports_generated.append(report)

                # Validate headers
                expected_headers = ['run_id', 'cycle_id', 'RRN', 'UPI_Transaction_ID', 'Amount',
                                  'Transaction_Date', 'RC', 'Source_System_1', 'Source_System_2',
                                  'Direction', 'Matched_On']
                actual_headers = list(df.columns)
                if set(expected_headers).issubset(set(actual_headers)):
                    print(f"  ✓ Headers validated")
                else:
                    print(f"  ✗ Header mismatch. Expected: {expected_headers}, Got: {actual_headers}")
            else:
                print(f"✗ {report}: NOT FOUND")
                errors.append(f"Missing: {report}")

    except Exception as e:
        print(f"✗ Error in matched reports: {e}")
        errors.append(f"Matched reports error: {e}")

    # Test 2: Unmatched Ageing Reports
    print("\n" + "=" * 80)
    print("TEST 2: Unmatched Ageing Reports")
    print("=" * 80)
    try:
        engine.generate_unmatched_ageing(test_data, run_folder, run_id, cycle_id)
        reports_dir = os.path.join(run_folder, 'reports')

        ageing_reports = ['Unmatched_Inward_Ageing.csv', 'Unmatched_Outward_Ageing.csv']

        for report in ageing_reports:
            path = os.path.join(reports_dir, report)
            if os.path.exists(path):
                df = pd.read_csv(path)
                size = os.path.getsize(path)
                print(f"✓ {report}: {len(df)} records ({size} bytes)")
                reports_generated.append(report)

                # Validate ageing buckets
                if 'Ageing_Bucket' in df.columns:
                    buckets = df['Ageing_Bucket'].unique()
                    print(f"  ✓ Ageing buckets: {list(buckets)}")
                else:
                    print(f"  ✗ Missing Ageing_Bucket column")
            else:
                print(f"✗ {report}: NOT FOUND")
                errors.append(f"Missing: {report}")

    except Exception as e:
        print(f"✗ Error in ageing reports: {e}")
        errors.append(f"Ageing reports error: {e}")

    # Test 3: Hanging Reports
    print("\n" + "=" * 80)
    print("TEST 3: Hanging Transaction Reports")
    print("=" * 80)
    try:
        engine.generate_hanging_reports(test_data, run_folder, run_id, cycle_id)
        reports_dir = os.path.join(run_folder, 'reports')

        hanging_reports = ['Hanging_Inward.csv', 'Hanging_Outward.csv']

        for report in hanging_reports:
            path = os.path.join(reports_dir, report)
            if os.path.exists(path):
                df = pd.read_csv(path)
                size = os.path.getsize(path)
                print(f"✓ {report}: {len(df)} records ({size} bytes)")
                reports_generated.append(report)

                # Validate hanging reasons
                if 'Reason' in df.columns:
                    reasons = df['Reason'].unique()
                    print(f"  ✓ Hanging reasons: {list(reasons)}")
            else:
                print(f"✗ {report}: NOT FOUND")
                errors.append(f"Missing: {report}")

    except Exception as e:
        print(f"✗ Error in hanging reports: {e}")
        errors.append(f"Hanging reports error: {e}")

    # Test 4: Adjustments/Annexure Reports
    print("\n" + "=" * 80)
    print("TEST 4: Adjustments/Annexure Reports")
    print("=" * 80)
    try:
        engine.generate_adjustments_csv(test_data, run_folder, run_id, cycle_id)
        reports_dir = os.path.join(run_folder, 'reports')

        adjustments_file = 'adjustments.csv'
        path = os.path.join(run_folder, adjustments_file)
        if os.path.exists(path):
            df = pd.read_csv(path)
            size = os.path.getsize(path)
            print(f"✓ {adjustments_file}: {len(df)} records ({size} bytes)")
            reports_generated.append(adjustments_file)

            # Check for TCC candidates
            tcc_count = len(df[df['Suggested_Action'].str.contains('TCC', na=False)])
            print(f"  ✓ TCC candidates: {tcc_count}")
        else:
            print(f"✗ {adjustments_file}: NOT FOUND")
            errors.append(f"Missing: {adjustments_file}")

    except Exception as e:
        print(f"✗ Error in adjustments: {e}")
        errors.append(f"Adjustments error: {e}")

    # Test 5: TTUM Files
    print("\n" + "=" * 80)
    print("TEST 5: TTUM Files Generation")
    print("=" * 80)
    try:
        ttum_files = settlement_engine.generate_ttum_files(test_data, run_folder)
        ttum_dir = os.path.join(run_folder, 'ttum')

        ttum_categories = ['drc', 'rrc', 'tcc', 'ret', 'refund', 'recovery']

        for category in ttum_categories:
            if category in ttum_files:
                path = ttum_files[category]
                if os.path.exists(path):
                    df = pd.read_csv(path)
                    size = os.path.getsize(path)
                    print(f"✓ {category.upper()}.csv: {len(df)} records ({size} bytes)")
                    reports_generated.append(f"{category}.csv")
                else:
                    print(f"✗ {category.upper()}.csv: NOT FOUND")
                    errors.append(f"Missing TTUM: {category}.csv")
            else:
                print(f"✗ {category.upper()}: NOT GENERATED")
                errors.append(f"Missing TTUM: {category}")

    except Exception as e:
        print(f"✗ Error in TTUM generation: {e}")
        errors.append(f"TTUM error: {e}")

    # Test 6: Switch Update File
    print("\n" + "=" * 80)
    print("TEST 6: Switch Update File")
    print("=" * 80)
    try:
        engine.generate_switch_update_file(test_data, run_folder, run_id)
        reports_dir = os.path.join(run_folder, 'reports')

        switch_file = 'Switch_Update_File.csv'
        path = os.path.join(reports_dir, switch_file)
        if os.path.exists(path):
            df = pd.read_csv(path)
            size = os.path.getsize(path)
            print(f"✓ {switch_file}: {len(df)} records ({size} bytes)")
            reports_generated.append(switch_file)
        else:
            print(f"✗ {switch_file}: NOT FOUND")
            errors.append(f"Missing: {switch_file}")

    except Exception as e:
        print(f"✗ Error in switch update: {e}")
        errors.append(f"Switch update error: {e}")

    # Test 7: Summary and JSON files
    print("\n" + "=" * 80)
    print("TEST 7: Summary and JSON Files")
    print("=" * 80)
    try:
        # Generate summary
        summary_path = engine.generate_summary_json(test_data, run_folder)
        if os.path.exists(summary_path):
            size = os.path.getsize(summary_path)
            print(f"✓ summary.json: {size} bytes")
            reports_generated.append('summary.json')

            # Validate JSON structure
            with open(summary_path, 'r') as f:
                summary = json.load(f)
            required_keys = ['run_id', 'generated_at', 'totals', 'matched', 'unmatched', 'hanging', 'exceptions']
            if all(key in summary for key in required_keys):
                print(f"  ✓ JSON structure validated")
            else:
                print(f"  ✗ Missing keys in summary.json")
        else:
            print(f"✗ summary.json: NOT FOUND")
            errors.append("Missing: summary.json")

        # Generate human report
        report_path = engine.generate_human_report(test_data, run_folder, run_id)
        if os.path.exists(report_path):
            size = os.path.getsize(report_path)
            print(f"✓ report.txt: {size} bytes")
            reports_generated.append('report.txt')
        else:
            print(f"✗ report.txt: NOT FOUND")
            errors.append("Missing: report.txt")

    except Exception as e:
        print(f"✗ Error in summary/reports: {e}")
        errors.append(f"Summary error: {e}")

    # Test 8: Recon Output JSON
    print("\n" + "=" * 80)
    print("TEST 8: Recon Output JSON")
    print("=" * 80)
    try:
        recon_json_path = os.path.join(run_folder, 'reports', 'recon_output.json')
        if os.path.exists(recon_json_path):
            size = os.path.getsize(recon_json_path)
            print(f"✓ recon_output.json: {size} bytes")
            reports_generated.append('recon_output.json')

            # Validate JSON content
            with open(recon_json_path, 'r') as f:
                recon_data = json.load(f)
            if isinstance(recon_data, dict) and len(recon_data) > 0:
                print(f"  ✓ Contains {len(recon_data)} transaction records")
            else:
                print(f"  ✗ Invalid recon output structure")
        else:
            print(f"✗ recon_output.json: NOT FOUND")
            errors.append("Missing: recon_output.json")

    except Exception as e:
        print(f"✗ Error in recon output: {e}")
        errors.append(f"Recon output error: {e}")

    # Final Summary
    print("\n" + "=" * 100)
    print("FINAL TEST SUMMARY")
    print("=" * 100)

    print(f"✓ Total reports generated: {len(reports_generated)}")
    print(f"✓ Test run folder: {run_folder}")

    if errors:
        print(f"✗ Errors encountered: {len(errors)}")
        for error in errors:
            print(f"  - {error}")
    else:
        print("✓ All reports generated successfully!")

    # List all generated files
    print("
Generated files:")
    for root, dirs, files in os.walk(run_folder):
        for file in files:
            if file.endswith(('.csv', '.json', '.txt')):
                rel_path = os.path.relpath(os.path.join(root, file), run_folder)
                size = os.path.getsize(os.path.join(root, file))
                print(f"  {rel_path} ({size} bytes)")

    print("\n" + "=" * 100)
    print("COMPREHENSIVE REPORT TEST COMPLETED")
    print("=" * 100)

    return run_id, run_folder, len(reports_generated), len(errors)

if __name__ == "__main__":
    run_id, run_folder, reports_count, errors_count = test_all_reports()
    print(f"\nTest Results:")
    print(f"Run ID: {run_id}")
    print(f"Run Folder: {run_folder}")
    print(f"Reports Generated: {reports_count}")
    print(f"Errors: {errors_count}")

    if errors_count == 0:
        print("🎉 ALL REPORTS GENERATED SUCCESSFULLY!")
    else:
        print("⚠️  Some reports had errors - check above for details")
