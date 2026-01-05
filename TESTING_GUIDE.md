# Testing Guide - Frontend Data Display Issues

## Issues Fixed
1. ✅ Rollback.tsx:414 error - "Cannot read properties of undefined"
2. ✅ View file upload shows nothing
3. ✅ Unmatched report not displaying
4. ✅ Force match not working

---

## Test Scenario: Complete Workflow

### Step 1: Upload Files
**Expected:** View file upload displays all uploaded files

```
Navigate to: File Upload → View file upload tab
Expected Display:
- CBS/GL File section
  ✓ CBS Inward File (uploaded)
  ✓ CBS Outward File (uploaded) 
  ✓ Switch File (uploaded)
- NPCI Files section
  ✓ NPCI Inward Raw (if uploaded)
  ✓ NPCI Outward Raw (if uploaded)
```

**What was fixed:**
- `/api/v1/upload/metadata` now returns `uploaded_files` array instead of failing with 404
- ViewStatus.tsx can parse the response properly

**Expected Response:**
```json
{
  "run_id": "RUN_20260105_120000",
  "uploaded_files": ["cbs_inward", "cbs_outward", "switch"],
  "saved_files": {...},
  "status": "success"
}
```

---

### Step 2: Run Reconciliation
**Expected:** Reconciliation completes and creates run output

```
Navigate to: Recon page → Run Reconciliation
Expected: Run completes with RUN_ID generated
```

---

### Step 3: Check Unmatched Report
**Expected:** Unmatched tab shows transactions with mismatches

```
Navigate to: Unmatched page
Expected Display:
- NPCI Unmatched Transactions table
- CBS Unmatched Transactions table
- Filters: Date range, Amount range, etc.
```

**What was fixed:**
- `/api/v1/reports/unmatched` now converts exceptions array to RRN-keyed dictionary
- Unmatched.tsx `transformReportToUnmatched()` can properly iterate the data

**Expected Response:**
```json
{
  "run_id": "RUN_20260105_120000",
  "data": {
    "RRN000001": {
      "rrn": "RRN000001",
      "status": "ORPHAN",
      "cbs": {...},
      "switch": null,
      "npci": {...}
    },
    "RRN000002": {...}
  },
  "format": "upi",
  "summary": {...}
}
```

---

### Step 4: Access Rollback Page
**Expected:** Rollback page loads without errors

```
Navigate to: Rollback page
Expected Without Errors:
- Dropdown to select a run
- Rollback level selection (whole_process, cycle_wise)
```

**What was fixed:**
- `/api/v1/rollback/available-cycles` now returns `available_cycles` key (was `cycles`)
- Line 414 error in Rollback.tsx fixed by correcting the API response

**Expected Response:**
```json
{
  "run_id": "RUN_20260105_120000",
  "status": "success",
  "available_cycles": ["1A", "1B", "1C", "2A", "2B", "2C"],
  "total_available": 6,
  "all_cycles": ["1A", "1B", "1C", "2A", "2B", "2C"]
}
```

---

### Step 5: Select Cycle-Wise Rollback
**Expected:** Cycle selector appears with available cycles

```
Navigate to: Rollback → Granular Rollback Tab
Select Rollback Level: "cycle_wise"
Expected:
- "NPCI Cycle ID" dropdown appears
- Shows available cycles: 1A, 1B, 1C, etc.
- Can select a cycle and initiate rollback
```

**Critical Fix:** The dropdown now populates because:
- Backend returns `available_cycles` array (was returning `cycles`)
- Frontend line 414 can now call `.map()` on the array

---

### Step 6: Check Force Match
**Expected:** Force Match page displays unmatched transactions

```
Navigate to: Force Match page
Expected Display:
- Table of unmatched/mismatched transactions
- Can select a transaction to compare
- Shows CBS, Switch, NPCI data side-by-side
```

**What was fixed:**
- `/api/v1/recon/latest/raw` now converts exceptions array to RRN-keyed dictionary
- ForceMatch.tsx `transformRawDataToTransactions()` can iterate `Object.entries(rawData.data)`

**Expected Response:**
```json
{
  "run_id": "RUN_20260105_120000",
  "data": {
    "RRN000001": {
      "status": "ORPHAN",
      "cbs": {...},
      "switch": null,
      "npci": {...}
    }
  },
  "format": "upi"
}
```

---

## API Endpoints Modified

| Endpoint | Issue | Fix | Expected Response |
|----------|-------|-----|-------------------|
| `/api/v1/upload/metadata` | 404 on missing metadata | Return empty metadata gracefully | `{uploaded_files, status}` |
| `/api/v1/summary/historical` | Wrong structure | Extract transaction counts | `[{month, allTxns, reconciled}]` |
| `/api/v1/reports/unmatched` | Array format not RRN-keyed | Convert exceptions to dict | `{data: {rrn: record}}` |
| `/api/v1/recon/latest/raw` | Array format not RRN-keyed | Convert exceptions to dict | `{data: {rrn: record}}` |
| `/api/v1/rollback/available-cycles` | Wrong key name | Changed `cycles` → `available_cycles` | `{available_cycles, status}` |

---

## Rollback Verification

After testing upload/unmatched/force-match, try rollback:

1. Navigate to Rollback page
   - ✓ Page loads without error
   - ✓ Run history populates
   
2. Select a run
   - ✓ Cycle options appear
   
3. Select cycle_wise rollback
   - ✓ Cycle dropdown shows cycles without error
   
4. Initiate rollback
   - ✓ Confirmation dialog appears
   - ✓ Rollback executes

---

## Browser Console Check

After each navigation, check browser console (F12) for:
- ❌ No TypeErrors
- ❌ No undefined reference errors
- ✓ Any errors should be caught gracefully with toast notifications

---

## Database Verify

Check file system for proper data structure:

```
OUTPUT_DIR/
  RUN_20260105_120000/
    recon_output.json  (UPI format)
    reports/
      cycle_1A/
      cycle_1B/
    ttum/

UPLOAD_DIR/
  RUN_20260105_120000/
    metadata.json      (with run details)
```

---

## Success Criteria

✅ All tests pass without console errors
✅ Rollback page loads and cycles populate
✅ Unmatched shows transactions properly formatted
✅ Force Match displays data correctly
✅ View file upload shows uploaded files list
