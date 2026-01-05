# Integration Testing Checklist ✅

## Pre-Testing Setup

- [ ] Backend uvicorn server is running on port 8000
- [ ] Frontend dev server is running on port 5173
- [ ] Test data files are available in test directory

---

## Test Scenario 1: File Upload Flow ✅

### Step 1: Upload Files
```
GO TO: http://localhost:5173/file-upload
ACTION: Select CBS Inward, CBS Outward, Switch files → Upload
EXPECT: Toast showing "Files uploaded successfully"
BACKEND: Saves metadata.json to UPLOAD_DIR/RUN_XXXXXXX/
```

### Step 2: View Upload Status
```
GO TO: http://localhost:5173/file-upload (View File Upload tab)
ACTION: Click "Refresh Status"
EXPECT: Shows all uploaded files with checkmarks
BACKEND CALL: GET /api/v1/upload/metadata
  Returns: {uploaded_files: ["cbs_inward", "cbs_outward", "switch"]}
```

**Integration Check:**
- ✅ Frontend calls `apiClient.getUploadMetadata()`
- ✅ Backend returns `{uploaded_files: array}`
- ✅ Frontend transforms array to UI display

---

## Test Scenario 2: Reconciliation Flow ✅

### Step 1: Run Reconciliation
```
GO TO: http://localhost:5173/recon
ACTION: Select cycle/direction → Click "Run Recon"
EXPECT: Reconciliation runs and shows results
BACKEND: 
  - Calls UPI engine (or legacy engine)
  - Saves recon_output.json to OUTPUT_DIR/RUN_XXXXXXX/
```

### Step 2: View Dashboard
```
GO TO: http://localhost:5173/
ACTION: Dashboard loads
EXPECT: Shows totals, matched, unmatched, etc.
BACKEND CALL: GET /api/v1/summary
  Returns: {run_id, totals, matched, unmatched, ...}
```

**Integration Check:**
- ✅ Frontend calls `apiClient.getSummary()`
- ✅ Backend reads from OUTPUT_DIR for UPI or UPLOAD_DIR for legacy
- ✅ Frontend displays reconciliation stats

---

## Test Scenario 3: Rollback Flow ✅

### Step 1: Load Rollback Page
```
GO TO: http://localhost:5173/rollback
ACTION: Page loads
EXPECT: Shows run history table
BACKEND CALL: GET /api/v1/summary/historical
  Returns: [{month: "2026-01", allTxns: 1112, reconciled: 0}]
```

### Step 2: Select Run
```
ACTION: Click on a run in history
ACTION: If cycle-wise, cycles dropdown appears
BACKEND CALL: GET /api/v1/rollback/available-cycles?run_id=RUN_XXXXXXX
  Returns: {available_cycles: ["20260105_1C", "20260105_2C"]}
```

### Step 3: Execute Rollback
```
ACTION: Select rollback level → Click "Rollback"
EXPECT: Confirmation dialog → Rollback executes
BACKEND CALL: POST /api/v1/rollback/[type]?run_id=RUN_XXXXXXX
  Returns: {status: "ok", result: ...}
```

**Integration Check:**
- ✅ Frontend calls `apiClient.getHistoricalSummary()`
- ✅ Backend parses recon_output.json and extracts transaction counts
- ✅ Frontend calls `apiClient.getAvailableCycles(run_id)`
- ✅ Backend scans OUTPUT_DIR for cycle folders
- ✅ Frontend displays cycles in dropdown

---

## Test Scenario 4: Unmatched Report ✅

### Step 1: Navigate to Unmatched
```
GO TO: http://localhost:5173/unmatched
ACTION: Page loads
EXPECT: Table with unmatched transactions
BACKEND CALL: GET /api/v1/reports/unmatched
```

### Step 2: Verify Data Structure
```
BACKEND RESPONSE (for UPI):
{
  "run_id": "RUN_20260105_160947",
  "data": {
    "RRN123": {
      "source": "CBS",
      "rrn": "RRN123",
      "amount": 100.0,
      "date": "2026-01-05",
      "exception_type": "ORPHAN",
      ...
    }
  }
}

FRONTEND TRANSFORMS TO:
{
  source: "CBS",
  rrn: "RRN123",
  amount: 100.0,
  amountFormatted: "₹100",
  tranDate: "2026-01-05",
  ...
}
```

### Step 3: Check Table Display
```
EXPECT: 
  - RRN column shows transaction ID
  - Amount column shows formatted amount
  - Source column shows origin system
  - Can search, filter, export
```

**Integration Check:**
- ✅ Frontend calls `apiClient.getReport("unmatched")`
- ✅ Backend converts UPI exceptions array to RRN-keyed dict
- ✅ Frontend transforms dict to array for table display
- ✅ Data fields align (rrn, amount, date, source)

---

## Test Scenario 5: ForceMatch Page ✅

### Step 1: Navigate to ForceMatch
```
GO TO: http://localhost:5173/force-match
ACTION: Page loads
EXPECT: List of unmatched transactions with full details
BACKEND CALL: GET /api/v1/recon/latest/raw
```

### Step 2: Verify Transaction Details
```
BACKEND RESPONSE (for UPI - converted from exceptions):
{
  "run_id": "RUN_20260105_160947",
  "data": {
    "RRN123": {
      "rrn": "RRN123",
      "status": "ORPHAN",
      "cbs": {
        "rrn": "RRN123",
        "amount": 100.0,
        "date": "2026-01-05",
        "reference": "..."
      },
      "source": "cbs"
    }
  }
}

FRONTEND TRANSFORMS TO:
{
  rrn: "RRN123",
  status: "ORPHAN",
  cbs: {rrn, amount, date, reference, ...},
  switch: undefined,
  npci: undefined,
  suggested_action: "Investigate missing in Switch, NPCI"
}
```

### Step 3: Test Force Match Action
```
ACTION: Click on transaction → Select source systems → Force Match
EXPECT: Match executed successfully
BACKEND CALL: POST /api/v1/force-match?rrn=RRN123&source1=cbs&source2=npci
  Returns: {status: "ok", action: "matched", ...}
```

**Integration Check:**
- ✅ Frontend calls `apiClient.getRawData()`
- ✅ Backend converts UPI exceptions to transaction format with source-specific fields
- ✅ Frontend transformation expects cbs/switch/npci objects
- ✅ All fields present and properly mapped

---

## Test Scenario 6: Reports Download ✅

### Step 1: Navigate to Reports
```
GO TO: http://localhost:5173/reports
ACTION: Page loads
EXPECT: List of available report types
```

### Step 2: Download Report
```
ACTION: Click on "Matched" report → Download
BACKEND CALL: GET /api/v1/reports/matched
  Returns: ZIP or JSON blob
EXPECT: File downloads with name "matched_report_RUN_XXXXXXX.zip"
```

### Step 3: Download Adjustments
```
ACTION: Click "Download Adjustments"
BACKEND CALL: GET /api/v1/recon/latest/adjustments
  Returns: CSV blob
EXPECT: File downloads as "adjustments_RUN_XXXXXXX.csv"
```

### Step 4: Download TTUM Variants
```
ACTION: Request "/api/v1/reports/ttum/csv"
BACKEND: Returns CSV with TTUM data
EXPECT: File downloads as "ttum_report_RUN_XXXXXXX.csv"

ACTION: Request "/api/v1/reports/ttum/xlsx"
BACKEND: Returns XLSX with formatted headers
EXPECT: File downloads as "ttum_report_RUN_XXXXXXX.xlsx"
```

**Integration Check:**
- ✅ Frontend calls `apiClient.downloadLatestReport()`, etc.
- ✅ Backend returns FileResponse with proper media type
- ✅ Browser triggers download with correct filename

---

## Common Issues & Troubleshooting

### Issue 1: "Cannot read properties of undefined (reading 'map')" in Rollback
**Cause:** Backend returns `cycles` instead of `available_cycles`
**Fix Status:** ✅ FIXED - Now returns `available_cycles`
**Verify:** Check backend line 1703

### Issue 2: Unmatched page shows empty
**Cause:** Backend returns exceptions array instead of RRN-keyed dict
**Fix Status:** ✅ FIXED - Now converts to RRN-keyed format
**Verify:** Check backend line 1300

### Issue 3: ForceMatch page shows nothing
**Cause:** Raw data missing cbs/switch/npci fields
**Fix Status:** ✅ FIXED - Now maps exceptions to proper transaction format
**Verify:** Check backend line 1454

### Issue 4: View Upload Status shows "No uploads"
**Cause:** Backend returns 404 instead of graceful empty response
**Fix Status:** ✅ FIXED - Now returns {uploaded_files: []}
**Verify:** Check backend line 1205

### Issue 5: Rollback page not loading
**Cause:** Historical summary returns wrong format
**Fix Status:** ✅ FIXED - Now returns [{month, allTxns, reconciled}]
**Verify:** Check backend line 627

---

## Success Criteria

- [ ] All files upload successfully
- [ ] View Upload Status shows uploaded files
- [ ] Reconciliation completes without errors
- [ ] Dashboard shows correct transaction counts
- [ ] Rollback page shows run history and cycles
- [ ] Unmatched page shows all unmatched transactions
- [ ] ForceMatch page shows transactions with full details
- [ ] Force match action successfully matches transactions
- [ ] Reports download in all formats (JSON, CSV, XLSX)
- [ ] No console errors in browser DevTools
- [ ] No Python exceptions in server logs

---

## Sign-Off

Once all tests pass:
- ✅ Integration is complete
- ✅ Backend and frontend are synchronized
- ✅ Ready for production deployment
