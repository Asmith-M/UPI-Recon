#!/usr/bin/env python3
"""
Test script to verify ageing reports generation with cycle_id fixes
"""

import os
import sys
import tempfile
from datetime import datetime, timedelta

# Add the backend directory to Python path
sys.path.insert(0, os.path.dirname(__file__))

from recon_engine import ReconciliationEngine

def test_ageing_reports_with_cycle_id():
    """Test that ageing reports generate correctly with cycle_id parameter"""

    # Create temporary output directory
    with tempfile.TemporaryDirectory() as temp_dir:
        # Initialize reconciliation engine
        engine = ReconciliationEngine(output_dir=temp_dir)

        # Sample recon results with unmatched transactions and hanging
        recon_results = {
            '123456789012': {
                'status': 'ORPHAN',
                'cbs': {
                    'RRN': '123456789012',
                    'amount': 100.50,
                    'date': (datetime.now() - timedelta(days=5)).strftime('%Y-%m-%d'),
                    'dr_cr': 'D'
                }
            },
            '987654321098': {
                'status': 'PARTIAL_MATCH',
                'switch': {
                    'RRN': '987654321098',
                    'amount': 200.75,
                    'date': (datetime.now() - timedelta(days=10)).strftime('%Y-%m-%d'),
                    'dr_cr': 'C'
                }
            },
            '555666777888': {
                'status': 'HANGING',
                'cbs': {
                    'RRN': '555666777888',
                    'amount': 300.00,
                    'date': (datetime.now() - timedelta(days=2)).strftime('%Y-%m-%d'),
                    'dr_cr': 'C'
                },
                'switch': {
                    'RRN': '555666777888',
                    'amount': 300.00,
                    'date': (datetime.now() - timedelta(days=2)).strftime('%Y-%m-%d'),
                    'dr_cr': 'C'
                },
                'hanging_reason': 'CBS and SWITCH present, NPCI missing'
            }
        }

        # Create a temporary run folder
        run_folder = os.path.join(temp_dir, 'test_run')
        os.makedirs(run_folder, exist_ok=True)

        print("Testing ageing reports generation with cycle_id...")

        try:
            # Test generate_unmatched_ageing with cycle_id
            ageing_path = engine.generate_unmatched_ageing(
                recon_results,
                run_folder,
                run_id='TEST_RUN_001',
                cycle_id='1C'
            )

            if ageing_path and os.path.exists(ageing_path):
                print(f"✅ Ageing report generated: {ageing_path}")

                # Check if cycle_id is in the file
                with open(ageing_path, 'r') as f:
                    content = f.read()
                    if '1C' in content:
                        print("✅ Cycle ID '1C' found in ageing report")
                    else:
                        print("❌ Cycle ID '1C' not found in ageing report")
                        return False
            else:
                print("❌ Ageing report not generated")
                return False

            # Test generate_hanging_reports with cycle_id
            hanging_path = engine.generate_hanging_reports(
                recon_results,
                run_folder,
                run_id='TEST_RUN_001',
                cycle_id='1C'
            )

            if hanging_path and os.path.exists(hanging_path):
                print(f"✅ Hanging report generated: {hanging_path}")

                # Check if cycle_id is in the file
                with open(hanging_path, 'r') as f:
                    content = f.read()
                    if '1C' in content:
                        print("✅ Cycle ID '1C' found in hanging report")
                    else:
                        print("❌ Cycle ID '1C' not found in hanging report")
                        return False
            else:
                print("❌ Hanging report not generated")
                return False

            # Test generate_adjustments_csv with cycle_id
            adjustments_path = engine.generate_adjustments_csv(
                recon_results,
                run_folder,
                run_id='TEST_RUN_001',
                cycle_id='1C'
            )

            if adjustments_path and os.path.exists(adjustments_path):
                print(f"✅ Adjustments report generated: {adjustments_path}")
            else:
                print("❌ Adjustments report not generated")
                return False

            print("🎉 All ageing and adjustment reports generated successfully with cycle_id!")
            return True

        except Exception as e:
            print(f"❌ Test failed with error: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == '__main__':
    success = test_ageing_reports_with_cycle_id()
    sys.exit(0 if success else 1)
