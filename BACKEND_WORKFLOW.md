# Backend Workflow Documentation

## Overview

The UPI Reconciliation System backend is built with **FastAPI** and handles all the core reconciliation logic, data processing, and settlement operations. It processes financial transaction data from multiple sources (CBS, Switch, NPCI, NTSL) and automatically matches transactions to identify discrepancies.

---

## System Architecture

### Tech Stack
- **Framework**: FastAPI (Python)
- **Authentication**: JWT (JSON Web Tokens) with HS256 algorithm
- **Database**: JSON-based file storage
- **Session Management**: 30-minute token expiration

---

## API Endpoints & Workflows

### 1. **Authentication & Authorization**

#### Login Workflow
```
User Request (username + password) → FastAPI /auth/login
    ↓
Verify Credentials (against USERS_DB)
    ↓
Hash Password & Compare
    ↓
Generate JWT Token (30 min expiration)
    ↓
Return Token + User Info
    ↓
Frontend stores in localStorage
```

**Endpoint**: `POST /api/v1/auth/login`
- **Input**: `{ username: string, password: string }`
- **Output**: `{ access_token: string, token_type: "bearer", user: {...} }`
- **Default Credentials**: 
  - Username: `admin`
  - Password: `admin123`

#### Token Validation
```
Protected Route Request (with Bearer Token)
    ↓
Extract Token from Authorization Header
    ↓
Validate JWT Signature (HS256)
    ↓
Check Token Expiration (30 min TTL)
    ↓
Decode & Get Username
    ↓
Lookup User in USERS_DB
    ↓
Attach User to Request
    ↓
Process Request
```

**Endpoint**: `GET /api/v1/auth/me`
- **Requires**: Valid Bearer token
- **Output**: Current user details (username, email, roles)

---

### 2. **File Upload & Processing**

#### File Upload Workflow
```
User Uploads Files (CBS, Switch, NPCI, NTSL)
    ↓
Frontend sends MultiPart Form Data to /api/v1/upload
    ↓
Backend Validation
    - Check file formats (Excel/CSV)
    - Validate file sizes
    - Verify required fields
    ↓
Create Run Directory (RUN_YYYYMMDD_HHMMSS)
    ↓
Extract & Normalize Data
    - Map column names per config
    - Handle missing values
    - Format dates & amounts
    ↓
Store in Upload Directory
    ↓
Trigger Reconciliation Engine
    ↓
Return Summary to Frontend
```

**Endpoint**: `POST /api/v1/upload`
- **Input**: Multipart file upload (CBS Inward, CBS Outward, Switch, NPCI files, etc.)
- **Output**: 
  ```json
  {
    "status": "success",
    "run_id": "RUN_20260105_123456",
    "files_uploaded": 5,
    "processing_status": "in_progress"
  }
  ```
- **Storage Path**: `/data/uploads/RUN_YYYYMMDD_HHMMSS/`

---

### 3. **Reconciliation Engine**

#### Core Reconciliation Workflow
```
Input Files Loaded (CBS, Switch, NPCI, NTSL data)
    ↓
Data Normalization
    - Standardize column names
    - Parse dates & amounts
    - Handle missing values
    ↓
Transaction Matching Logic
    ├─ Exact Match: RRN + Amount + Date + Source
    ├─ Partial Match: Amount & Date variations (tolerance)
    ├─ Mismatch: Amount/Date differences
    └─ Orphan: No matching record found
    ↓
Generate Match Status for Each Transaction
    ├─ MATCHED
    ├─ PARTIAL_MATCH
    ├─ PARTIAL_MISMATCH
    ├─ ORPHAN
    ├─ HANGING
    ├─ DUPLICATE
    ├─ FORCE_MATCHED (manual matches)
    └─ PROCESSING_ERROR
    ↓
Create Summary Report
    - Total transactions
    - Match rate %
    - Exception counts
    ↓
Settlement Engine Processing (if enabled)
    ↓
Generate Output Files & Reports
```

**Key Classes**:
- `ReconciliationEngine`: Core reconciliation logic
- `UPIReconciliationEngine`: UPI-specific matching rules

**Matching Rules**:
1. **Exact Match**: RRN, Amount, Date, and Transaction Type all match
2. **Partial Match**: Amount and Date match within tolerance, minor differences in RRN
3. **Orphan**: Transaction in one source but not found in others
4. **Hanging**: Transaction not yet matched but still processing

**Endpoint**: `POST /api/v1/recon/run`
- **Triggers**: Automatic after file upload
- **Output**: Reconciliation results saved to JSON files

---

### 4. **Settlement & GL Proofing**

#### Settlement Engine Workflow
```
Matched Transactions
    ↓
Generate Vouchers
    ├─ PAYMENT: Regular transactions
    ├─ REVERSAL: Reversed entries
    ├─ ADJUSTMENT: Manual adjustments
    └─ SETTLEMENT: Settlement entries
    ↓
Create GL Entries
    - Debit/Credit mapping
    - Account code assignment
    ↓
Generate Settlement Report
    - Voucher summary
    - GL entries listing
    - Balance reconciliation
    ↓
Export to CSV (Annexure IV format)
```

**Endpoint**: `GET /api/v1/reports/settlement`
- **Output**: Settlement summary and GL entries

#### GL Proofing Workflow
```
GL Entries Generated
    ↓
Variance Analysis
    - Compare GL balance vs. reconciled balance
    - Identify discrepancies
    ↓
Bridging Logic
    - Auto-balance adjustments
    - Exception flagging
    ↓
Generate GL Proof Report
    - Variance details
    - Reconciliation status
```

**Endpoint**: `GET /api/v1/reports/gl-proofing`
- **Output**: GL proofing results with variance analysis

---

### 5. **Exception & Anomaly Handling**

#### Exception Handling Workflow
```
Transaction Processing
    ↓
Exception Detected
    ├─ Matching error
    ├─ Data validation error
    ├─ Processing failure
    └─ Network timeout
    ↓
Classify Exception Type
    ↓
Log to Exception Queue
    ↓
Create Exception Record
    - Transaction details
    - Error description
    - Recommended action
    ↓
Make Reviewable in UI (Exception Dashboard)
```

**Endpoint**: `GET /api/v1/exceptions`
- **Output**: List of unhandled exceptions

---

### 6. **Audit Trail**

#### Audit Logging Workflow
```
Every API Call / Data Modification
    ↓
Capture Event Details
    - User who performed action
    - Timestamp
    - Action type (upload, reconcile, force-match, rollback)
    - Resource affected
    - Before/After state
    ↓
Write to Audit Log
    - File: `/data/output/audit_logs/audit_trail_YYYYMMDD.json`
    - Format: JSON array of events
    ↓
Queryable via API
```

**Endpoint**: `GET /api/v1/audit`
- **Output**: Audit trail entries (filterable by date, user, action type)

---

### 7. **Rollback Management**

#### Rollback Workflow
```
User Initiates Rollback
    ↓
Select Rollback Level
    ├─ FULL: Revert to initial upload state
    ├─ PARTIAL: Revert last reconciliation run
    └─ SELECTIVE: Revert specific records
    ↓
Validate Rollback Feasibility
    - Check audit trail
    - Verify no dependencies
    ↓
Load Previous State from History
    ↓
Revert Data
    - Restore original files
    - Clear reconciliation results
    - Reset match status
    ↓
Log Rollback Action
    ↓
Update Frontend
```

**Endpoint**: `POST /api/v1/recon/rollback`
- **Input**: `{ run_id: string, level: "full" | "partial" | "selective" }`
- **Output**: Rollback confirmation

**Rollback Storage**: `/data/outputs/rollback_history.json`

---

### 8. **Query & Reporting APIs**

#### Summary Query
```
/api/v1/summary → Latest Reconciliation Summary
    - Total transactions
    - Matched count & %
    - Unmatched count
    - Exception count
    - Run timestamp
```

#### Unmatched Records Query
```
/api/v1/recon/latest/unmatched → Orphan & Unmatched Transactions
    - Full transaction details
    - Source information
    - Recommended actions
```

#### Hanging Transactions Query
```
/api/v1/recon/latest/hanging → Transactions Still Processing
    - Partial matches
    - Pending manual review
```

#### Force Match
```
/api/v1/force-match → Manual Transaction Matching
    Input: { transaction_id_1, transaction_id_2, match_notes }
    
    Workflow:
    ├─ Validate transactions exist
    ├─ Check compatibility
    ├─ Create forced match record
    ├─ Update reconciliation status
    └─ Log action to audit trail
```

#### Enquiry API
```
/api/v1/enquiry → Transaction Search
    Input: { search_term, filter_type }
    
    Returns:
    ├─ Exact transaction match
    ├─ Related transactions
    └─ Historical records
```

---

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    USER (Frontend Browser)                       │
│                                                                  │
│  Login → Auth Token → Upload Files → Reconciliation → Reports  │
└──────────────────────────┬──────────────────────────────────────┘
                           │ HTTP/HTTPS
                           ↓
┌─────────────────────────────────────────────────────────────────┐
│              FASTAPI BACKEND (Authentication Layer)              │
│                                                                  │
│  JWT Token Validation & User Authorization                      │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ↓
┌─────────────────────────────────────────────────────────────────┐
│         FILE HANDLER → DATA NORMALIZATION → VALIDATION           │
│                                                                  │
│  ├─ CBS Files (Inward, Outward, Balance)                        │
│  ├─ Switch Files                                                │
│  ├─ NPCI Files (Inward, Outward)                                │
│  ├─ NTSL Files                                                  │
│  └─ Adjustment Files                                            │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ↓
┌─────────────────────────────────────────────────────────────────┐
│      RECONCILIATION ENGINE (Core Matching Logic)                 │
│                                                                  │
│  ├─ Transaction Matching Algorithm                              │
│  ├─ Exception Detection & Flagging                              │
│  ├─ Duplicate Handling                                          │
│  └─ Status Assignment (MATCHED/ORPHAN/HANGING/etc)              │
└──────────────────────────┬──────────────────────────────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
        ↓                  ↓                  ↓
   ┌────────────┐    ┌────────────┐   ┌─────────────┐
   │Settlement  │    │  GL        │   │   Audit     │
   │Engine      │    │  Proofing  │   │   Trail     │
   │(Vouchers)  │    │(Variance)  │   │ (Logging)   │
   └────────────┘    └────────────┘   └─────────────┘
        │                  │                  │
        └──────────────────┼──────────────────┘
                           │
                           ↓
┌─────────────────────────────────────────────────────────────────┐
│            OUTPUT & STORAGE (JSON Files)                         │
│                                                                  │
│  ├─ summary.json (reconciliation summary)                       │
│  ├─ unmatched_records.json                                      │
│  ├─ settlement_RUN_*.json                                       │
│  ├─ audit_trail_YYYYMMDD.json                                   │
│  ├─ rollback_history.json                                       │
│  └─ reports/ (XLSX/CSV exports)                                 │
└──────────────────────────┬──────────────────────────────────────┘
                           │ HTTP
                           ↓
┌─────────────────────────────────────────────────────────────────┐
│              FRONTEND (Dashboard & Reports)                      │
│                                                                  │
│  ├─ Summary Cards                                               │
│  ├─ Charts & Visualizations                                     │
│  ├─ Exception Lists                                             │
│  ├─ Manual Match Interface                                      │
│  └─ Rollback Controls                                           │
└─────────────────────────────────────────────────────────────────┘
```

---

## Configuration Files

### `config.py`
- Upload and output directory paths
- Database configuration
- Tolerance levels for matching

### `config/ttum_mapping.json`
- Column name mapping for input files
- Data type specifications
- Required vs. optional fields

### `config/roles.json`
- User role definitions
- Permission mappings

---

## Key Components

### `file_handler.py`
Handles file uploads and initial processing:
- File validation
- Format detection (Excel/CSV)
- Column mapping
- Data extraction

### `recon_engine.py`
Core reconciliation logic:
- Transaction matching algorithm
- Exception detection
- Duplicate handling
- Status assignment

### `settlement_engine.py`
Settlement accounting:
- Voucher generation
- GL entry creation
- Balance reconciliation

### `audit_trail.py`
Audit logging:
- Event tracking
- User action logging
- State snapshots

### `rollback_manager.py`
Rollback functionality:
- State restoration
- History management
- Multi-level rollback

### `exception_handler.py`
Exception management:
- Error classification
- Exception queuing
- Remediation suggestions

---

## Error Handling Strategy

1. **Validation Errors** (400)
   - Invalid file format
   - Missing required fields
   - Data type mismatches

2. **Authentication Errors** (401)
   - Invalid credentials
   - Expired token
   - Missing authorization

3. **Resource Errors** (404)
   - File not found
   - Record not found

4. **Server Errors** (500)
   - Processing failures
   - Database errors
   - System exceptions

All errors are logged with:
- Timestamp
- User info
- Request details
- Error trace

---

## Performance Considerations

- **Large File Processing**: Files are processed in chunks to avoid memory overflow
- **Token Expiration**: 30-minute sessions to balance security and UX
- **Caching**: Summary data cached to reduce repeated calculations
- **Async Processing**: File uploads trigger background reconciliation jobs

---

## Security Implementation

1. **JWT Authentication**: Secure token-based authentication
2. **Password Hashing**: SHA256 hashing for stored passwords
3. **CORS Configuration**: Restricted to frontend origin
4. **Bearer Tokens**: Authorization header validation
5. **Audit Trail**: All actions logged for compliance

---

## Deployment Notes

- **Environment Variables**:
  - `FRONTEND_ORIGIN`: CORS origin (default: `http://localhost:5173`)
  - `SECRET_KEY`: JWT signing key (change in production)

- **Production Checklist**:
  - [ ] Change `SECRET_KEY` in production
  - [ ] Update `ALLOWED_ORIGINS` for CORS
  - [ ] Configure environment variables
  - [ ] Enable HTTPS
  - [ ] Set up database backups
  - [ ] Configure audit log retention

---

## Monitoring & Logs

All system operations are logged to:
- **Application Logs**: `logging_config.py`
- **Audit Trail**: `/data/output/audit_logs/`
- **Error Logs**: Captured in response payloads

Monitor key metrics:
- API response times
- Error rates
- Reconciliation success rate
- Token expiration frequency
