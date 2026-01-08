"""
Test script to verify report generation fixes
Run this after a reconciliation to check if all reports are generated correctly
"""

import os
import sys

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from config import OUTPUT_DIR

def check_reports(run_id):
    """Check if all required reports are generated for a run"""
    
    reports_dir = os.path.join(OUTPUT_DIR, run_id, 'reports')
    
    if not os.path.exists(reports_dir):
        print(f"❌ Reports directory not found: {reports_dir}")
        return False
    
    print(f"✅ Reports directory exists: {reports_dir}")
    print(f"\nChecking for required reports...\n")
    
    # Required reports
    required_reports = {
        'Core Reports': [
            'matched_transactions.csv',
            'matched_transactions.xlsx',
            'unmatched_exceptions.csv',
            'unmatched_exceptions.xlsx',
            'ttum_candidates.csv',
            'ttum_candidates.xlsx',
        ],
        'Pairwise Matched Reports': [
            'GL_vs_Switch_Inward.csv',
            'GL_vs_Switch_Outward.csv',
            'Switch_vs_NPCI_Inward.csv',
            'Switch_vs_NPCI_Outward.csv',
            'GL_vs_NPCI_Inward.csv',
            'GL_vs_NPCI_Outward.csv',
        ],
        'Ageing Reports': [
            'Unmatched_Inward_Ageing.csv',
            'Unmatched_Outward_Ageing.csv',
        ],
        'Hanging Reports': [
            'Hanging_Inward.csv',
            'Hanging_Outward.csv',
        ]
    }
    
    all_found = True
    
    for category, reports in required_reports.items():
        print(f"📁 {category}:")
        for report in reports:
            report_path = os.path.join(reports_dir, report)
            if os.path.exists(report_path):
                size = os.path.getsize(report_path)
                print(f"  ✅ {report} ({size} bytes)")
            else:
                print(f"  ❌ {report} - NOT FOUND")
                all_found = False
        print()
    
    # List all files in reports directory
    print("📋 All files in reports directory:")
    try:
        all_files = os.listdir(reports_dir)
        for f in sorted(all_files):
            file_path = os.path.join(reports_dir, f)
            size = os.path.getsize(file_path)
            print(f"  - {f} ({size} bytes)")
    except Exception as e:
        print(f"  ❌ Error listing files: {e}")
    
    print()
    
    if all_found:
        print("✅ All required reports are present!")
    else:
        print("❌ Some reports are missing. Check the reconciliation process.")
    
    return all_found

def get_latest_run():
    """Get the latest run ID"""
    try:
        runs = [d for d in os.listdir(OUTPUT_DIR) if d.startswith('RUN_')]
        if not runs:
            return None
        return sorted(runs)[-1]
    except Exception as e:
        print(f"Error getting latest run: {e}")
        return None

if __name__ == "__main__":
    print("=" * 60)
    print("UPI Reconciliation - Report Generation Test")
    print("=" * 60)
    print()
    
    # Get run_id from command line or use latest
    if len(sys.argv) > 1:
        run_id = sys.argv[1]
    else:
        run_id = get_latest_run()
        if not run_id:
            print("❌ No runs found in OUTPUT_DIR")
            print(f"OUTPUT_DIR: {OUTPUT_DIR}")
            sys.exit(1)
        print(f"Using latest run: {run_id}")
    
    print()
    success = check_reports(run_id)
    
    print()
    print("=" * 60)
    
    sys.exit(0 if success else 1)
