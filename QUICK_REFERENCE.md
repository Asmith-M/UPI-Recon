# Report Generation Fix - Quick Reference

## Problem Summary
Reports were not being generated correctly in the output directory. Issues included:
1. Empty reports
2. Wrong format
3. Reports not being generated at all
4. Frontend couldn't download reports due to missing endpoints

## Solution Applied

### 1. Backend Changes (`app.py`)
✅ Added new comprehensive endpoint: `/api/v1/reports/{report_type}`
- Handles ALL frontend report requests
- Maps frontend report names to backend file patterns
- Searches in both OUTPUT_DIR and UPLOAD_DIR
- Supports all report categories

### 2. Report Generation Enhancement (`recon_engine.py`)
✅ Enhanced `generate_upi_report()` method to create:
- Pairwise matched reports (GL vs Switch, Switch vs NPCI, GL vs NPCI)
- Ageing reports with buckets (0-1 days, 2-3 days, >3 days)
- Hanging transaction reports
- All reports in both CSV and XLSX formats

### 3. New Helper Methods
✅ `_generate_pairwise_reports()` - Creates matched reports for each system pair
✅ `_generate_ageing_reports_from_exceptions()` - Creates ageing analysis
✅ `_generate_hanging_reports_from_exceptions()` - Creates hanging transaction reports

## Reports Generated

### Core Reports (Always Generated)
- `matched_transactions.csv` / `.xlsx`
- `unmatched_exceptions.csv` / `.xlsx`
- `ttum_candidates.csv` / `.xlsx`

### Pairwise Reports (Inward & Outward)
- `GL_vs_Switch_Inward.csv` / `GL_vs_Switch_Outward.csv`
- `Switch_vs_NPCI_Inward.csv` / `Switch_vs_NPCI_Outward.csv`
- `GL_vs_NPCI_Inward.csv` / `GL_vs_NPCI_Outward.csv`

### Ageing Reports
- `Unmatched_Inward_Ageing.csv`
- `Unmatched_Outward_Ageing.csv`

### Hanging Reports
- `Hanging_Inward.csv`
- `Hanging_Outward.csv`

## Testing

### 1. Run Test Script
```bash
cd backend
python test_report_generation.py [RUN_ID]
```
This will check if all required reports are present.

### 2. Manual Verification
```bash
# Check reports directory
ls -la data/output/<RUN_ID>/reports/

# Count CSV files
ls data/output/<RUN_ID>/reports/*.csv | wc -l
# Should be at least 13 files
```

### 3. Frontend Testing
1. Login to frontend
2. Navigate to Reports page
3. Try downloading from each tab:
   - Listing Reports
   - Reconciliation Reports (Inward/Outward)
   - TTUM & Annexure
   - Legacy Reports

## API Endpoints

### New Endpoint (Handles All Reports)
```
GET /api/v1/reports/{report_type}
```

Examples:
```bash
# Listing report
GET /api/v1/reports/cbs_beneficiary

# Reconciliation report
GET /api/v1/reports/recon/gl_vs_switch/matched/inward

# Annexure report
GET /api/v1/reports/annexure/iv/bulk
```

### Legacy Endpoints (Still Work)
```
GET /api/v1/reports/matched/csv
GET /api/v1/reports/unmatched/csv
GET /api/v1/reports/ttum/csv
GET /api/v1/reports/ageing
GET /api/v1/reports/hanging
```

## Troubleshooting

### Reports Not Generated
1. ✅ Check reconciliation completed: `GET /api/v1/recon/latest/summary`
2. ✅ Check logs: `tail -f backend/logs/app_*.log`
3. ✅ Verify OUTPUT_DIR permissions: `ls -la data/output/`

### Empty Reports
1. ✅ Check input files have data
2. ✅ Verify `recon_output.json` has exceptions
3. ✅ Check direction field in exceptions

### Frontend Download Fails
1. ✅ Check backend is running: `curl http://localhost:8000/health`
2. ✅ Verify authentication token
3. ✅ Check browser console for errors
4. ✅ Verify report_type matches backend mapping

## Files Modified
1. ✅ `backend/app.py` - New endpoint
2. ✅ `backend/recon_engine.py` - Enhanced report generation
3. ✅ `backend/test_report_generation.py` - Test script
4. ✅ `REPORT_GENERATION_FIX.md` - Full documentation
5. ✅ `QUICK_REFERENCE.md` - This file

## Next Steps
1. Run a full reconciliation
2. Execute test script to verify reports
3. Test frontend downloads
4. Monitor for any issues
5. Adjust report formats based on user feedback

## Support
If issues persist:
1. Check `REPORT_GENERATION_FIX.md` for detailed documentation
2. Run `test_report_generation.py` for diagnostics
3. Check backend logs for errors
4. Verify all files are in correct locations
