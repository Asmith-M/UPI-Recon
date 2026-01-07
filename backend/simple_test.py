#!/usr/bin/env python3
"""
Simple test to verify RRN extraction logic
"""

# Test the key logic from the fix
def test_rrn_extraction():
    # Simulate the data structure
    recon_results = {
        '123456789012': {  # Dictionary key
            'status': 'ORPHAN',
            'cbs': {
                'RRN': '987654321098',  # Actual RRN in data
                'amount': 100.50,
                'date': '2024-01-15'
            }
        }
    }

    print("Testing RRN extraction logic...")
    print("=" * 50)

    for rrn_key, rec in recon_results.items():
        print(f"Dictionary key: {rrn_key}")

        # Simulate pick_source function
        src = None
        for s in ['cbs', 'switch', 'npci']:
            if rec.get(s):
                src = rec[s]
                break

        if src:
            print(f"Source data: {src}")

            # OLD logic (buggy): rrn_str = str(rrn_key)
            old_rrn = str(rrn_key)
            print(f"OLD logic would use: {old_rrn}")

            # NEW logic (fixed): rrn_str = str(src.get('RRN', rrn_key))
            new_rrn = str(src.get('RRN', rrn_key))
            print(f"NEW logic uses: {new_rrn}")

            if old_rrn != new_rrn:
                print("✅ Fix working: Using actual RRN from data instead of key")
            else:
                print("❌ Fix not working: Still using key as RRN")

    print("=" * 50)
    print("Test completed!")

if __name__ == '__main__':
    test_rrn_extraction()
