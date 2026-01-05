# Frontend Report Endpoints Verification

## Status: ✅ ALL ENDPOINTS AVAILABLE

### Report Endpoints Summary

| Report Type | Frontend Calls | Backend Endpoint | Status |
|------------|----------------|--------------------|--------|
| **Matched** | `getReport('matched')` | `GET /api/v1/reports/matched` | ✅ |
| **Unmatched** | `getReport('unmatched')` | `GET /api/v1/reports/unmatched` | ✅ |
| **Summary** | `getReport('summary')` | `GET /api/v1/reports/summary` | ✅ |
| **TTUM** | `getReport('ttum')` | `GET /api/v1/reports/ttum` | ✅ |
| **TTUM CSV** | N/A (available) | `GET /api/v1/reports/ttum/csv` | ✅ |
| **TTUM XLSX** | N/A (available) | `GET /api/v1/reports/ttum/xlsx` | ✅ |
| **TTUM Merged** | N/A (available) | `GET /api/v1/reports/ttum/merged` | ✅ |
| **Adjustments** | `downloadLatestAdjustments()` | `GET /api/v1/recon/latest/adjustments` | ✅ |
| **Report (Text)** | `downloadLatestReport()` | `GET /api/v1/recon/latest/report` | ✅ |

---

## Key UPI Engine Endpoints (Phase 2)

### Reconciliation & Data Retrieval
- `GET /api/v1/recon/latest/raw` - Latest raw reconciliation data ✅
- `GET /api/v1/recon/latest/report` - Latest report (JSON for UPI, TXT for legacy) ✅
- `GET /api/v1/recon/latest/summary` - Latest summary ✅
- `GET /api/v1/summary` - Current summary (alias) ✅
- `GET /api/v1/summary/historical` - Historical summaries ✅

### Report Downloads
- `GET /api/v1/reports/matched` - Matched transactions ✅
- `GET /api/v1/reports/unmatched` - Unmatched/exception transactions ✅
- `GET /api/v1/reports/summary` - Summary report ✅
- `GET /api/v1/reports/ttum` - TTUM data (ZIP format) ✅
- `GET /api/v1/reports/ttum/csv` - TTUM as CSV(s) ✅ (NEW)
- `GET /api/v1/reports/ttum/xlsx` - TTUM as XLSX(s) ✅ (NEW)
- `GET /api/v1/reports/ttum/merged` - TTUM merged single file ✅ (NEW)

### Rollback Operations
- `POST /api/v1/rollback/whole-process` - Complete rollback ✅
- `POST /api/v1/rollback/cycle-wise` - Cycle-specific rollback ✅
- `POST /api/v1/rollback/ingestion` - File rollback ✅
- `POST /api/v1/rollback/mid-recon` - Mid-reconciliation rollback ✅
- `POST /api/v1/rollback/accounting` - Accounting rollback ✅

---

## Notes

### For UPI Reconciliation Results:
- Results are stored in `OUTPUT_DIR/<run_id>/recon_output.json`
- Report endpoints automatically detect UPI format and return appropriate structure
- Unmatched endpoint returns `exceptions` array for UPI format
- Raw data endpoint includes separate summary stats for UPI format

### For Legacy Reconciliation Results:
- Results are stored in `UPLOAD_DIR/<run_id>/recon_output.json` (nested by cycle/direction)
- Report endpoints fall back to legacy format if OUTPUT_DIR not found
- Unmatched endpoint returns legacy `unmatched` array
- Raw data endpoint includes traditional summary stats

### Data Directory Structure

**UPI Results (New):**
```
OUTPUT_DIR/
  RUN_XXXXXXX/
    recon_output.json  (UPI engine output with summary, exceptions, ttum_candidates)
```

**Legacy Results (Existing):**
```
UPLOAD_DIR/
  RUN_XXXXXXX/
    cycle_YYYYMMDD_XC/
      inward/
        file_mapping.json
        metadata.json
        recon_output.json
      outward/
```

---

## Frontend Integration Status

### Report Components Working:
- ✅ Download matched report
- ✅ Download unmatched report  
- ✅ Download summary
- ✅ Download TTUM (ZIP)
- ✅ Download adjustments CSV
- ✅ Download text report

### New Features Available:
- 📋 TTUM CSV export (`/api/v1/reports/ttum/csv`)
- 📋 TTUM XLSX export (`/api/v1/reports/ttum/xlsx`)
- 📋 TTUM merged export (`/api/v1/reports/ttum/merged`)

---

## Next Steps (Optional)

To expose new TTUM export options in frontend, add to `Reports.tsx`:

```typescript
{
  id: "ttum-csv",
  name: "TTUM Report (CSV)", 
  description: "TTUM data in CSV format",
  endpoint: "ttum/csv"
},
{
  id: "ttum-xlsx",
  name: "TTUM Report (Excel)", 
  description: "TTUM data in Excel format with formatting",
  endpoint: "ttum/xlsx"
},
{
  id: "ttum-merged",
  name: "TTUM Report (Merged)", 
  description: "All TTUM data merged into single file",
  endpoint: "ttum/merged"
}
```

Then update `handleDownloadReport` to handle these new types with appropriate file extensions.
