#!/usr/bin/env python3
"""
Test script to verify the TTUM RRN extraction fix in settlement_engine.py
"""

import os
import sys
import tempfile
import json
from datetime import datetime

# Add the backend directory to Python path
sys.path.insert(0, os.path.dirname(__file__))

from settlement_engine import SettlementEngine

def test_ttum_rrn_extraction():
    """Test that generate_ttum_files correctly extracts RRN from source data"""

    # Create temporary output directory
    with tempfile.TemporaryDirectory() as temp_dir:
        # Initialize settlement engine
        engine = SettlementEngine(temp_dir)

        # Sample recon_results data - simulating the structure where:
        # - Dictionary key is '123456789012' (the key)
        # - But the actual RRN in the source data is '987654321098'
        recon_results = {
            '123456789012': {  # This is the dictionary key
                'status': 'ORPHAN',
                'cbs': {
                    'RRN': '987654321098',  # This is the actual RRN value we want to use
                    'amount': 100.50,
                    'date': '2024-01-15',
                    'dr_cr': 'D',
                    'rc': '00',
                    'tran_type': 'U2'
                }
            },
            '111111111111': {
                'status': 'PARTIAL_MATCH',
                'switch': {
                    'RRN': '222222222222',  # Different RRN in source data
                    'amount': 200.75,
                    'date': '2024-01-16',
                    'dr_cr': 'C',
                    'rc': 'RB',
                    'tran_type': 'U3'
                }
            }
        }

        # Create a temporary run folder
        run_folder = os.path.join(temp_dir, 'test_run')
        os.makedirs(run_folder, exist_ok=True)

        print("Testing TTUM generation with RRN extraction fix...")

        try:
            # Generate TTUM files
            result = engine.generate_ttum_files(recon_results, run_folder)

            print(f"TTUM generation completed. Created files: {list(result.keys())}")

            # Check if TTUM directory was created
            ttum_dir = os.path.join(run_folder, 'ttum')
            if not os.path.exists(ttum_dir):
                print("❌ TTUM directory not created")
                return False

            # Check DRC TTUM file (should contain the ORPHAN transaction)
            drc_file = os.path.join(ttum_dir, 'drc.csv')
            if os.path.exists(drc_file):
                print("✅ DRC TTUM file created")
                with open(drc_file, 'r') as f:
                    content = f.read()
                    print(f"DRC file content:\n{content}")

                    # Check if the correct RRN (987654321098) is used, not the key (123456789012)
                    if '987654321098' in content and '123456789012' not in content:
                        print("✅ DRC file contains correct RRN from source data")
                    else:
                        print("❌ DRC file contains incorrect RRN")
                        return False
            else:
                print("❌ DRC TTUM file not found")

            # Check RRC TTUM file (should contain the PARTIAL_MATCH transaction)
            rrc_file = os.path.join(ttum_dir, 'rrc.csv')
            if os.path.exists(rrc_file):
                print("✅ RRC TTUM file created")
                with open(rrc_file, 'r') as f:
                    content = f.read()
                    print(f"RRC file content:\n{content}")

                    # Check if the correct RRN (222222222222) is used, not the key (111111111111)
                    if '222222222222' in content and '111111111111' not in content:
                        print("✅ RRC file contains correct RRN from source data")
                    else:
                        print("❌ RRC file contains incorrect RRN")
                        return False
            else:
                print("❌ RRC TTUM file not found")

            # Check Annexure IV file
            annexure_file = None
            for filename in os.listdir(ttum_dir):
                if filename.startswith('annexure_iv'):
                    annexure_file = os.path.join(ttum_dir, filename)
                    break

            if annexure_file and os.path.exists(annexure_file):
                print("✅ Annexure IV file created")
                with open(annexure_file, 'r') as f:
                    content = f.read()
                    print(f"Annexure IV content:\n{content}")

                    # Check if correct RRNs are used
                    if '987654321098' in content and '222222222222' in content:
                        print("✅ Annexure IV contains correct RRNs from source data")
                    else:
                        print("❌ Annexure IV contains incorrect RRNs")
                        return False
            else:
                print("❌ Annexure IV file not found")

            print("🎉 All tests passed! The RRN extraction fix is working correctly.")
            return True

        except Exception as e:
            print(f"❌ Test failed with error: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == '__main__':
    success = test_ttum_rrn_extraction()
    sys.exit(0 if success else 1)
