#!/usr/bin/env python3
"""
Test script to verify the TTUM cycle subdirectory fix in settlement_engine.py
"""

import os
import sys
import tempfile
import json
from datetime import datetime

# Add the backend directory to Python path
sys.path.insert(0, os.path.dirname(__file__))

from settlement_engine import SettlementEngine

def test_ttum_cycle_subdirectory():
    """Test that generate_ttum_files creates files in cycle subdirectory when cycle_id is provided"""

    # Create temporary output directory
    with tempfile.TemporaryDirectory() as temp_dir:
        # Initialize settlement engine
        engine = SettlementEngine(temp_dir)

        # Sample recon_results data
        recon_results = {
            '123456789012': {
                'status': 'ORPHAN',
                'cbs': {
                    'RRN': '987654321098',
                    'amount': 100.50,
                    'date': '2024-01-15',
                    'dr_cr': 'D',
                    'rc': '00',
                    'tran_type': 'U2'
                }
            }
        }

        # Create a temporary run folder
        run_folder = os.path.join(temp_dir, 'test_run')
        os.makedirs(run_folder, exist_ok=True)

        print("Testing TTUM generation with cycle subdirectory...")

        try:
            # Test 1: Generate TTUM files WITHOUT cycle_id (should go to /ttum/)
            result1 = engine.generate_ttum_files(recon_results, run_folder, run_id='TEST_RUN_001')

            ttum_dir = os.path.join(run_folder, 'ttum')
            if os.path.exists(ttum_dir):
                files_in_root = [f for f in os.listdir(ttum_dir) if f.endswith('.csv')]
                print(f"✅ Without cycle_id: {len(files_in_root)} files in /ttum/: {files_in_root}")
            else:
                print("❌ TTUM directory not created")
                return False

            # Test 2: Generate TTUM files WITH cycle_id (should go to /ttum/cycle_1C/)
            result2 = engine.generate_ttum_files(recon_results, run_folder, run_id='TEST_RUN_002', cycle_id='1C')

            cycle_dir = os.path.join(ttum_dir, 'cycle_1C')
            if os.path.exists(cycle_dir):
                files_in_cycle = [f for f in os.listdir(cycle_dir) if f.endswith('.csv')]
                print(f"✅ With cycle_id='1C': {len(files_in_cycle)} files in /ttum/cycle_1C/: {files_in_cycle}")

                # Check if files are actually in cycle directory
                if files_in_cycle:
                    print("✅ TTUM files correctly placed in cycle subdirectory")
                else:
                    print("❌ No files found in cycle subdirectory")
                    return False
            else:
                print("❌ Cycle subdirectory not created")
                return False

            # Test 3: Verify that files are not duplicated in root ttum directory
            files_in_root_after = [f for f in os.listdir(ttum_dir) if f.endswith('.csv') and os.path.isfile(os.path.join(ttum_dir, f))]
            print(f"ℹ️ Files in root /ttum/ after cycle run: {files_in_root_after}")

            print("🎉 All tests passed! The cycle subdirectory fix is working correctly.")
            return True

        except Exception as e:
            print(f"❌ Test failed with error: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == '__main__':
    success = test_ttum_cycle_subdirectory()
    sys.exit(0 if success else 1)
