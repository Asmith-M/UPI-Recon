# Report Generation Fix - UPI Reconciliation System

## Issues Identified

### 1. **Frontend-Backend Endpoint Mismatch**
- Frontend requests specific report endpoints (e.g., `recon/gl_vs_switch/matched/inward`) that don't exist in backend
- Backend generates reports but doesn't expose proper download endpoints for all report types

### 2. **Report Generation Issues**
- Reports being generated are empty or in wrong format
- Missing pairwise reports (GL vs Switch, Switch vs NPCI, GL vs NPCI)
- Missing ageing reports for unmatched transactions
- Missing hanging transaction reports

### 3. **Output Directory Structure**
- Reports should be in `C:\Users\asmit\OneDrive\Desktop\UPI-recon\UPI-Recon\backend\data\output\<RUN_ID>\reports\`
- Some reports were being generated in wrong locations or not at all

## Fixes Applied

### 1. **New Backend Endpoint** (`app.py`)
Added a comprehensive endpoint to handle all frontend report requests:

```python
@app.get("/api/v1/reports/{report_type}")
async def download_specific_report(report_type: str, ...)
```

This endpoint:
- Maps frontend report types to backend file patterns
- Searches in both OUTPUT_DIR and UPLOAD_DIR
- Handles all report categories:
  - Listing reports (CBS, Switch, NPCI raw data)
  - Reconciliation reports (matched/unmatched by direction)
  - TTUM and Annexure reports
  - Hanging transaction reports

**Report Mapping:**
```python
report_mapping = {
    # Listing reports
    'cbs_beneficiary': ['cbs_beneficiary', 'cbs_inward', 'listing_1'],
    'cbs_remitter': ['cbs_remitter', 'cbs_outward', 'listing_2'],
    'switch_inward': ['switch_inward', 'listing_3'],
    'switch_outward': ['switch_outward', 'listing_4'],
    'npci_inward': ['npci_inward', 'listing_5'],
    'npci_outward': ['npci_outward', 'listing_6'],
    
    # Reconciliation reports
    'recon/gl_vs_switch/matched/inward': ['GL_vs_Switch_Inward'],
    'recon/gl_vs_switch/matched/outward': ['GL_vs_Switch_Outward'],
    'recon/switch_vs_network/matched/inward': ['Switch_vs_NPCI_Inward'],
    'recon/switch_vs_network/matched/outward': ['Switch_vs_NPCI_Outward'],
    'recon/gl_vs_network/matched/inward': ['GL_vs_NPCI_Inward'],
    'recon/gl_vs_network/matched/outward': ['GL_vs_NPCI_Outward'],
    
    # Unmatched with ageing
    'recon/gl_vs_switch/unmatched/inward': ['Unmatched_Inward_Ageing'],
    'recon/gl_vs_switch/unmatched/outward': ['Unmatched_Outward_Ageing'],
    
    # Hanging transactions
    'recon/hanging_transactions/inward': ['Hanging_Inward'],
    'recon/hanging_transactions/outward': ['Hanging_Outward'],
    
    # TTUM and Annexure
    'annexure/i/raw': ['annexure_i', 'ANNEXURE_I'],
    'annexure/ii/raw': ['annexure_ii', 'ANNEXURE_II'],
    'annexure/iii/adjustment': ['annexure_iii', 'ANNEXURE_III'],
    'annexure/iv/bulk': ['annexure_iv', 'ANNEXURE_IV'],
}
```

### 2. **Enhanced UPI Report Generation** (`recon_engine.py`)
Enhanced `generate_upi_report()` method to generate all required reports:

**New Reports Generated:**
1. **Pairwise Matched Reports:**
   - `GL_vs_Switch_Inward.csv`
   - `GL_vs_Switch_Outward.csv`
   - `Switch_vs_NPCI_Inward.csv`
   - `Switch_vs_NPCI_Outward.csv`
   - `GL_vs_NPCI_Inward.csv`
   - `GL_vs_NPCI_Outward.csv`

2. **Ageing Reports:**
   - `Unmatched_Inward_Ageing.csv` (with ageing buckets: 0-1 days, 2-3 days, >3 days)
   - `Unmatched_Outward_Ageing.csv`

3. **Hanging Transaction Reports:**
   - `Hanging_Inward.csv`
   - `Hanging_Outward.csv`

4. **Existing Reports (Enhanced):**
   - `matched_transactions.csv` / `.xlsx`
   - `unmatched_exceptions.csv` / `.xlsx`
   - `ttum_candidates.csv` / `.xlsx`

**New Helper Methods:**
- `_generate_pairwise_reports()`: Creates matched transaction reports for each system pair
- `_generate_ageing_reports_from_exceptions()`: Creates ageing analysis reports
- `_generate_hanging_reports_from_exceptions()`: Creates hanging transaction reports

### 3. **Report Structure**
All reports now follow consistent structure:

**Matched Reports:**
```csv
run_id,cycle_id,RRN,Amount,Transaction_Date,Direction,Status
```

**Ageing Reports:**
```csv
run_id,cycle_id,RRN,Amount,Transaction_Date,Source,Exception_Type,Ageing_Days,Ageing_Bucket
```

**Hanging Reports:**
```csv
run_id,cycle_id,RRN,Amount,Transaction_Date,Source,Reason
```

## Testing the Fix

### 1. **Run Reconciliation**
```bash
# Upload files and run reconciliation
curl -X POST http://localhost:8000/api/v1/recon/run \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"run_id": "RUN_20260107_123456"}'
```

### 2. **Check Generated Reports**
```bash
# List all reports
ls -la C:\Users\asmit\OneDrive\Desktop\UPI-recon\UPI-Recon\backend\data\output\<RUN_ID>\reports\
```

Expected files:
- `matched_transactions.csv` / `.xlsx`
- `unmatched_exceptions.csv` / `.xlsx`
- `ttum_candidates.csv` / `.xlsx`
- `GL_vs_Switch_Inward.csv`
- `GL_vs_Switch_Outward.csv`
- `Switch_vs_NPCI_Inward.csv`
- `Switch_vs_NPCI_Outward.csv`
- `GL_vs_NPCI_Inward.csv`
- `GL_vs_NPCI_Outward.csv`
- `Unmatched_Inward_Ageing.csv`
- `Unmatched_Outward_Ageing.csv`
- `Hanging_Inward.csv`
- `Hanging_Outward.csv`

### 3. **Download Reports from Frontend**
1. Navigate to Reports page in frontend
2. Try downloading reports from each category:
   - Listing Reports
   - Reconciliation Reports (Inward/Outward)
   - TTUM & Annexure Reports
   - Legacy Reports

### 4. **Verify Report Content**
- Open CSV files and verify they contain data
- Check that columns match expected structure
- Verify ageing buckets are calculated correctly
- Ensure direction (INWARD/OUTWARD) is properly set

## API Endpoints Summary

### Download Specific Report
```
GET /api/v1/reports/{report_type}
```
Examples:
- `/api/v1/reports/cbs_beneficiary`
- `/api/v1/reports/recon/gl_vs_switch/matched/inward`
- `/api/v1/reports/annexure/iv/bulk`

### Legacy Endpoints (Still Supported)
- `/api/v1/reports/matched/csv`
- `/api/v1/reports/unmatched/csv`
- `/api/v1/reports/ttum/csv`
- `/api/v1/reports/ttum/xlsx`
- `/api/v1/reports/ageing`
- `/api/v1/reports/hanging`
- `/api/v1/reports/annexure`

## Troubleshooting

### Reports Not Generated
1. Check reconciliation completed successfully
2. Verify OUTPUT_DIR path is correct
3. Check logs for errors during report generation
4. Ensure write permissions on output directory

### Empty Reports
1. Verify input files have data
2. Check reconciliation results in `recon_output.json`
3. Ensure exceptions and ttum_candidates are populated
4. Check direction field is properly set in exceptions

### Frontend Can't Download
1. Verify backend endpoint is accessible
2. Check authentication token is valid
3. Verify report_type matches mapping in backend
4. Check browser console for errors

## Next Steps

1. **Test thoroughly** with real data
2. **Monitor logs** during reconciliation and report generation
3. **Verify all report types** are accessible from frontend
4. **Check report content** matches business requirements
5. **Add more report types** as needed based on user feedback

## Files Modified

1. `backend/app.py` - Added new endpoint for report downloads
2. `backend/recon_engine.py` - Enhanced UPI report generation
3. `REPORT_GENERATION_FIX.md` - This documentation

## Notes

- All reports are generated in CSV format for Excel compatibility
- XLSX versions are also generated for matched, unmatched, and TTUM reports
- Reports include run_id and cycle_id for traceability
- Ageing is calculated from transaction date to current date
- Direction (INWARD/OUTWARD) is inferred from debit_credit field
