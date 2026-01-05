# Frontend Data Display Issues - Fixes Summary

## Issues Reported
1. **View file upload** shows nothing
2. **Unmatched** report not displaying despite having unmatched data
3. **Force match** not working
4. **Rollback.tsx:414** - "Cannot read properties of undefined (reading 'map')" error

## Root Causes Identified

### 1. Rollback.tsx Error (Line 414)
**Issue:** Component tries to call `.map()` on `availableCycles.available_cycles` but backend returns `cycles` instead.

**Fix Applied:**
- Modified `/api/v1/rollback/available-cycles` endpoint response format
- Changed from: `{'run_id': run_id, 'cycles': [...]}`
- Changed to: `{'run_id': run_id, 'status': 'success', 'available_cycles': [...], 'total_available': N, 'all_cycles': [...]}`
- **File:** backend/app.py, line 1680

---

### 2. View File Upload (ViewStatus.tsx) Shows Nothing
**Issue:** ViewStatus.tsx calls `apiClient.getUploadMetadata()` and expects `metadata.uploaded_files` array, but backend:
- Throws 404 when metadata.json doesn't exist
- Returns raw metadata.json structure without `uploaded_files` key

**Fix Applied:**
- Modified `/api/v1/upload/metadata` endpoint to:
  - Return graceful empty response instead of 404
  - Transform `saved_files` dict to `uploaded_files` array for frontend
  - Include comprehensive response: `run_id`, `uploaded_files`, `saved_files`, `cycle_id`, `direction`, `run_date`, `status`
- **File:** backend/app.py, lines 1204-1248
- **Backend Response Format:**
  ```json
  {
    "run_id": "RUN_20260105_120000",
    "uploaded_files": ["cbs_inward", "cbs_outward", "switch"],
    "saved_files": {...},
    "cycle_id": "...",
    "direction": "inward",
    "run_date": "2026-01-05",
    "status": "success"
  }
  ```

---

### 3. Unmatched Report Not Displaying
**Issue:** 
- Unmatched.tsx expects `report.data` to be a key-value object indexed by RRN
- Backend returns exceptions as an array for UPI format
- Frontend's `transformReportToUnmatched()` expects dict keys to access transaction data

**Fix Applied:**
- Modified `/api/v1/reports/unmatched` endpoint to:
  - Convert UPI exceptions array to RRN-keyed dictionary
  - Return format: `{'run_id': latest, 'data': {rrn: record, ...}, 'format': 'upi'}`
  - Maintain backward compatibility with legacy format
- **File:** backend/app.py, lines 1299-1350
- **Backend Response Format:**
  ```json
  {
    "run_id": "RUN_20260105_120000",
    "data": {
      "RRN123456": {
        "rrn": "RRN123456",
        "status": "ORPHAN",
        "amount": 100.00,
        "date": "2026-01-05",
        ...
      },
      "RRN123457": {...}
    },
    "format": "upi",
    "summary": {...}
  }
  ```

---

### 4. Historical Summary Not Loading (Rollback.tsx Data Loading)
**Issue:** 
- Rollback.tsx calls `apiClient.getHistoricalSummary()` 
- Backend returns raw report.txt content without structured data
- Frontend's `fetchRunHistory()` expects objects with `month`, `allTxns`, `reconciled` keys

**Fix Applied:**
- Modified `/api/v1/summary/historical` endpoint to:
  - Parse run_id to extract date (RUN_YYYYMMDD_HHMMSS format)
  - Read recon_output.json from both OUTPUT_DIR (UPI) and UPLOAD_DIR (legacy)
  - Extract transaction counts from both UPI and legacy formats
  - Return structured data array: `[{run_id, month, allTxns, reconciled, unmatched}, ...]`
- **File:** backend/app.py, lines 627-685
- **Backend Response Format:**
  ```json
  [
    {
      "run_id": "RUN_20260105_120000",
      "month": "2026-01",
      "allTxns": 1000,
      "reconciled": 950,
      "unmatched": 50
    },
    ...
  ]
  ```

---

### 5. Force Match Not Loading Data
**Issue:**
- ForceMatch.tsx calls `apiClient.getRawData()` and expects `rawData.data` as RRN-keyed dictionary
- For UPI format, exceptions are returned as arrays
- Frontend's `transformRawDataToTransactions()` iterates `Object.entries(rawData.data)`

**Fix Applied:**
- Modified `/api/v1/recon/latest/raw` endpoint to:
  - Convert UPI exceptions array to RRN-keyed dictionary
  - Return either exceptions dict or details dict for UPI format
  - Maintain legacy format compatibility
- **File:** backend/app.py, lines 1452-1510
- **Backend Response Format:**
  ```json
  {
    "run_id": "RUN_20260105_120000",
    "data": {
      "RRN123456": {
        "rrn": "RRN123456",
        "status": "ORPHAN",
        "cbs": {...},
        "switch": null,
        "npci": {...}
      },
      ...
    },
    "format": "upi",
    "summary": {...}
  }
  ```

---

## Files Modified

| File | Lines | Changes |
|------|-------|---------|
| backend/app.py | 627-685 | Fixed `/api/v1/summary/historical` endpoint |
| backend/app.py | 1204-1248 | Fixed `/api/v1/upload/metadata` endpoint |
| backend/app.py | 1299-1350 | Fixed `/api/v1/reports/unmatched` endpoint |
| backend/app.py | 1452-1510 | Fixed `/api/v1/recon/latest/raw` endpoint |
| backend/app.py | 1680 | Fixed `/api/v1/rollback/available-cycles` endpoint |

---

## Testing Checklist

- [ ] Upload files and verify ViewStatus shows upload list
- [ ] Run reconciliation and check Rollback page loads cycle selector
- [ ] Verify Unmatched tab displays unmatched transactions
- [ ] Check Force Match page loads and shows transactions
- [ ] Confirm Rollback cycle-wise selection works without errors

---

## Frontend Components Fixed

1. **Rollback.tsx** (Line 414): Now receives `available_cycles` in correct format
2. **ViewStatus.tsx** (Line 41): Now receives `uploaded_files` array in metadata
3. **Unmatched.tsx** (Line 43): Now receives `data` as RRN-keyed dictionary
4. **ForceMatch.tsx** (Line 131): Now receives `data` as RRN-keyed dictionary for transformation

---

## Notes

- All endpoints now support both UPI and legacy reconciliation formats
- Graceful fallbacks prevent 404 errors when data doesn't exist yet
- Response formats maintained backward compatibility where possible
- Frontend transformation functions remain unchanged - backend now returns expected format
