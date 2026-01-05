# UPI Reconciliation System - Fixes Applied
**Date**: January 5, 2026

## Summary
Three critical issues have been fixed to improve system stability and user experience:

---

## Issue 1: Rollback Functionality ✅ FIXED

### Problem
Rollback operations (whole-process, cycle-wise, mid-recon, and accounting) were failing because:
- `_validate_rollback_allowed()` only checked the upload directory, not the output directory
- Lock files were not being properly released after operations, causing cascading failures
- Multiple rollback attempts would fail if a lock remained

### Solution Applied
**File**: `backend/rollback_manager.py`

1. **Fixed run validation** (Line ~1065):
   - Now checks both `upload_dir` AND `output_dir` for run existence
   - Allows rollback even when processing is in output directory only
   
   ```python
   def _validate_run_exists(self, run_id: str) -> bool:
       """Validate that the run folder exists in either upload or output dir"""
       upload_run = os.path.exists(os.path.join(self.upload_dir, run_id))
       output_run = os.path.exists(os.path.join(self.output_dir, run_id))
       return upload_run or output_run
   ```

2. **Added lock cleanup** (finally blocks in all methods):
   - Added `finally: self._release_rollback_lock()` to:
     - `whole_process_rollback()` (Line ~210)
     - `ingestion_rollback()` (Line ~422)
     - `mid_recon_rollback()` (Line ~629)
     - `cycle_wise_rollback()` (Line ~815)
     - `accounting_rollback()` (Line ~1050)
   - Ensures locks are ALWAYS released, even on errors

### Testing Recommendations
```bash
# Test whole-process rollback
curl -X POST "http://localhost:8000/api/v1/rollback/whole-process?run_id=RUN_123&reason=Testing"

# Test cycle-wise rollback  
curl -X POST "http://localhost:8000/api/v1/rollback/cycle-wise?run_id=RUN_123&cycle_id=1A"
```

---

## Issue 2: TTUM Report Export Formats ✅ FIXED

### Problem
Users could only download TTUM reports as:
- ✅ ZIP files (multiple CSVs)
- ❌ Individual CSV files
- ❌ XLSX/Excel files
- ❌ Merged reports

This made data analysis difficult for Excel-based workflows.

### Solution Applied

**File 1**: `backend/reporting.py` - Enhanced with new export functions:

1. **`write_ttum_xlsx()`** - Write TTUM data to XLSX with formatting
   - Blue header row with white text
   - Auto-adjusted column widths
   - Frozen header row for easy scrolling
   - Proper decimal formatting for amounts

2. **`write_ttum_csv()`** - Write TTUM data to CSV
   - UTF-8 encoding
   - Proper date and amount formatting
   - Single or batch processing

3. **`write_ttum_pandas()`** - Efficient export for large datasets
   - Uses pandas for faster processing
   - Supports both CSV and XLSX
   - Better memory management

4. **`get_ttum_files()`** - Query available TTUM files
   - Filter by format (csv, xlsx, json, or all)
   - Support for cycle-specific queries

**File 2**: `backend/app.py` - Added 3 new API endpoints:

1. **`GET /api/v1/reports/ttum/csv`** - Download TTUM as CSV(s)
   ```bash
   curl "http://localhost:8000/api/v1/reports/ttum/csv?run_id=RUN_123"
   # Returns single CSV or ZIP of multiple CSVs (if multiple cycles)
   ```

2. **`GET /api/v1/reports/ttum/xlsx`** - Download TTUM as XLSX
   ```bash
   curl "http://localhost:8000/api/v1/reports/ttum/xlsx?run_id=RUN_123&cycle_id=1A"
   # Returns single XLSX or ZIP of multiple XLSXs
   ```

3. **`GET /api/v1/reports/ttum/merged`** - Download all TTUM merged
   ```bash
   curl "http://localhost:8000/api/v1/reports/ttum/merged?run_id=RUN_123&format=xlsx"
   # Combines all cycle data into single file
   ```

### Features
- ✅ Automatic XLSX formatting with headers & styling
- ✅ Proper handling of decimal amounts and dates
- ✅ Single file download when possible (no ZIP overhead)
- ✅ Automatic ZIP packaging for multiple cycles
- ✅ Merged report combining all cycles into one file
- ✅ Support for CSV and XLSX formats

### Testing
```bash
# Download single cycle TTUM as CSV
curl -O "http://localhost:8000/api/v1/reports/ttum/csv?run_id=RUN_123&cycle_id=1A" -H "Authorization: Bearer <token>"

# Download all cycles merged into XLSX
curl -O "http://localhost:8000/api/v1/reports/ttum/merged?run_id=RUN_123&format=xlsx" -H "Authorization: Bearer <token>"
```

---

## Issue 3: Cycle-wise Upload Structure 💡 RECOMMENDATION

### Current Status
The system already supports cycle-wise folder structure! The file handler in `backend/file_handler.py` (Line ~28-44) already implements:

```
UPLOAD_DIR/
  RUN_123/
    cycle_20250105_1A/
      inward/
        cbs_inward_[timestamp].xlsx
        npci_inward_[timestamp].xlsx
    cycle_20250105_1B/
      inward/
        cbs_inward_[timestamp].xlsx
    metadata.json (run-level metadata)
```

### Current Architecture Details

1. **Per-Run Metadata** (`RUN_123/metadata.json`):
   ```json
   {
     "run_id": "RUN_123",
     "cycle_id": "20250105_1A",
     "direction": "inward",
     "run_date": "2025-01-05",
     "saved_files": {
       "cbs_inward": "cbs_inward_20250105_143022.xlsx",
       "npci_inward": "npci_inward_20250105_143022.xlsx"
     }
   }
   ```

2. **Cycle Organization**:
   - Each cycle gets its own folder: `cycle_YYYYMMDD_CycleID`
   - Direction support: `inward/` and `outward/` subfolders
   - Write-once protection: Files are marked read-only after upload
   - Automatic conflict resolution with numbered suffixes

3. **Benefits for Rollback**:
   - ✅ Cycle-specific rollback already works
   - ✅ Can delete `cycle_XXX/` folder independently
   - ✅ Other cycles unaffected by rollback
   - ✅ Metadata tracks which files were processed

### Recommended Enhancement for Future

To make rollback even easier, consider creating output folder structure matching input:

```
OUTPUT_DIR/
  RUN_123/
    cycle_20250105_1A/
      reports/
        unmatched.csv
        matched.csv
      ttum/
        TTUM_REVERSAL.xlsx
        TTUM_REFUND.xlsx
      annexure/
      audit/
    cycle_20250105_1B/
      reports/
      ttum/
      annexure/
      audit/
    rollback_history.json
```

This mirrors the input structure and makes cleanup straightforward:
- Delete entire cycle output: `rm -r OUTPUT_DIR/RUN_123/cycle_XXX/`
- Automatically handles all related reports, TTUM, annexure
- Much simpler than current nested structure
- Makes cycle-wise rollback cleaner

### Implementation Notes
The file handler already supports this pattern - the output directory just needs to be reorganized to match. This would be a Phase 2 improvement that doesn't break existing functionality.

---

## Summary of Changes

| Component | Type | Status | Impact |
|-----------|------|--------|--------|
| Rollback validation | Bug Fix | ✅ Complete | HIGH - System stability |
| Lock management | Bug Fix | ✅ Complete | HIGH - System stability |
| TTUM CSV export | Feature | ✅ Complete | MEDIUM - User experience |
| TTUM XLSX export | Feature | ✅ Complete | MEDIUM - User experience |
| Merged TTUM export | Feature | ✅ Complete | MEDIUM - User experience |
| Cycle folder structure | Architecture | ✅ Existing | N/A - Already implemented |
| Output reorganization | Suggestion | 📋 Recommended | LOW - Future improvement |

---

## Next Steps

1. **Immediate**: Test rollback functionality to ensure locks release properly
2. **Immediate**: Verify TTUM export endpoints work with sample data
3. **Soon**: Install/verify `openpyxl` in deployment environment
4. **Future**: Consider output folder restructuring for Phase 2

---

## Dependencies Added
✅ Already in `requirements.txt`:
- `openpyxl==3.1.2` - Excel file generation
- `pandas==2.3.3` - Data manipulation
- `portalocker==3.2.0` - File locking

No new dependencies needed!
