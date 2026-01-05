# Quick Fix Reference

## Problem: Rollback.tsx Line 414 Error

**Error Message:**
```
Rollback.tsx:414 Uncaught TypeError: Cannot read properties of undefined (reading 'map')
    at Rollback (Rollback.tsx:414:59)
```

**Root Cause:**
```tsx
// Line 414 in Rollback.tsx:
{availableCycles.available_cycles.map((cycle) => (  // ERROR: cycles was undefined
```

Backend was returning:
```json
{'cycles': ['1A', '1B']}  // WRONG KEY NAME
```

Frontend expected:
```json
{'available_cycles': ['1A', '1B']}  // CORRECT KEY NAME
```

---

## Fix Applied

**File:** backend/app.py
**Endpoint:** GET /api/v1/rollback/available-cycles
**Line:** 1680

**Before:**
```python
return JSONResponse(content={'run_id': run_id, 'cycles': sorted(list(cycles))})
```

**After:**
```python
available_cycles = sorted(list(cycles))
return JSONResponse(content={
    'run_id': run_id, 
    'status': 'success', 
    'available_cycles': available_cycles,  # ✅ CORRECT KEY
    'total_available': len(available_cycles),
    'all_cycles': available_cycles
})
```

**Result:** Rollback.tsx line 414 now successfully executes `availableCycles.available_cycles.map()`

---

## Related Fixes

### Issue 2: View File Upload Shows Nothing
**Endpoint:** GET /api/v1/upload/metadata
**Root Cause:** No `uploaded_files` key in response
**Fix:** Return structured response with `uploaded_files` array

### Issue 3: Unmatched Data Not Displaying
**Endpoint:** GET /api/v1/reports/unmatched
**Root Cause:** Returns array, expects RRN-keyed object
**Fix:** Convert exceptions array to `{rrn: record}` format

### Issue 4: Force Match Data Not Loading
**Endpoint:** GET /api/v1/recon/latest/raw
**Root Cause:** Returns array, expects RRN-keyed object
**Fix:** Convert exceptions array to `{rrn: record}` format

### Issue 5: Rollback History Not Loading
**Endpoint:** GET /api/v1/summary/historical
**Root Cause:** Returns raw text, expects structured objects
**Fix:** Parse and return `{month, allTxns, reconciled}` array

---

## All 5 Endpoints Fixed

| # | Endpoint | Key Change | Location |
|---|----------|-----------|----------|
| 1 | `/api/v1/rollback/available-cycles` | `cycles` → `available_cycles` | Line 1680 |
| 2 | `/api/v1/upload/metadata` | Added `uploaded_files` key | Lines 1204-1248 |
| 3 | `/api/v1/reports/unmatched` | Array → RRN dict format | Lines 1299-1350 |
| 4 | `/api/v1/recon/latest/raw` | Array → RRN dict format | Lines 1452-1510 |
| 5 | `/api/v1/summary/historical` | Raw text → structured array | Lines 627-685 |

---

## Verification

To verify fixes are working:

```bash
# Test 1: Check available cycles endpoint
curl "http://localhost:8000/api/v1/rollback/available-cycles?run_id=RUN_20260105_120000"

# Expected response includes:
# {
#   "available_cycles": [...],
#   "status": "success"
# }

# Test 2: Check upload metadata endpoint  
curl "http://localhost:8000/api/v1/upload/metadata"

# Expected response includes:
# {
#   "uploaded_files": [...],
#   "status": "success"
# }

# Test 3: Check unmatched report endpoint
curl "http://localhost:8000/api/v1/reports/unmatched"

# Expected response includes:
# {
#   "data": {
#     "RRN...": {...},
#     ...
#   }
# }
```

---

## Impact Summary

**Before Fixes:**
- ❌ Rollback page crashes on load
- ❌ View file upload shows empty
- ❌ Unmatched tab shows no data
- ❌ Force Match shows no transactions
- ❌ Console errors on multiple pages

**After Fixes:**
- ✅ Rollback page loads and functions
- ✅ View file upload displays uploaded files
- ✅ Unmatched tab displays unmatched transactions
- ✅ Force Match displays transactions properly
- ✅ No console errors
