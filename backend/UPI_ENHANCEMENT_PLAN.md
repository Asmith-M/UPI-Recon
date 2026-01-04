# UPI Reconciliation Enhancement Implementation Plan

## Overview
Based on the Verif.ai Functional Document for UPI Channel enhancements, this plan outlines the implementation of comprehensive UPI reconciliation features including file processing, validation, matching logic, TTUM generation, and settlement processes.

## Current Status
- ✅ Basic reconciliation framework exists
- ✅ File upload and basic validation implemented
- ✅ Core matching logic present
- ❌ UPI-specific features missing

## Phase 1: File Processing & Validation Enhancements

### 1.1 PGP Decryption Support
**Status:** On hold (as per document)
**Implementation:** Add PGP decryption capability for NPCI files
- Add PGP key management
- Implement decryption service
- Handle encrypted file processing

### 1.2 Enhanced File Validation
**Required Validations:**
- File format checks (Excel, CSV, TXT)
- Field structure validation
- Data accuracy checks
- Financial transaction identification logic:
  - Amount > 0
  - Tran_Type = 'U2' (Merchant) or 'U3' (Raw)
  - Valid Response Codes (RC validation)
- NPCI vs NTSL reconciliation checks

### 1.3 File Sources Enhancement
**Current:** Manual upload
**Add:**
- SFTP auto-scheduler with retry logic
- Database link via API integration
- Enhanced manual upload with search capabilities

## Phase 2: Data Ingestion & Listing Reports

### 2.1 Listing Reports Generation
**Required Reports:**
- CBS Beneficiary Listing (Inward)
- CBS Remitter Listing (Outward)
- Switch Listing (Inward/Outward)
- NPCI Beneficiary Listing (Inward)
- NPCI Remitter Listing (Outward)

### 2.2 File Dashboard
**Real-time Progress Tracking:**
- File Upload status
- File Validation status
- Data Ingestion status
- Cycle-wise visibility

## Phase 3: Advanced Reconciliation Logic

### 3.1 Matching Parameters Configuration
**Configurable Matching Rules:**
- Best Match: UPI_Tran_ID, RRN, Tran_Date, Tran_Amt
- Relaxed Match I: UPI_Tran_ID, Tran_Date, Tran_Amt
- Additional parameters as needed

### 3.2 UPI-Specific Recon Logic
**Outward Transaction Logic (in sequence):**
1. Cut-off transaction handling (Hanging transactions)
2. Self-matched transactions (Auto-reversed)
3. Settlement entries identification
4. Double debit/credit detection
5. Normal matching with RC '00'
6. Deemed accepted matching (RC 'RB' → TCC 102/103)
7. NPCI declined transaction handling
8. Failed auto-credit reversal handling

### 3.3 Transaction Categorization
**Status Types:**
- Matched Transactions
- Hanging Transactions
- Unmatched Transactions
- TCC 102/103 (Deemed accepted)
- RET (Return) transactions

## Phase 4: TTUM Generation & Exception Handling

### 4.1 TTUM Types Required
**Outward TTUMs:**
- Remitter Refund TTUM
- Remitter Recovery TTUM
- Failed Auto-credit/reversal
- Double Debit/Credit reversal
- NTSL Settlement TTUM
- DRC (Debit Reversal Confirmation)
- RRC (Return Reversal Confirmation)

**Inward TTUMs:**
- Beneficiary Recovery TTUM
- Beneficiary Credit TTUM
- TCC 102/103 processing
- RET file generation

### 4.2 Accounting Entries Configuration
**GL Account Configuration:**
- NPCI Settlement Account
- Payable/Receivable GL accounts
- Remitter/Beneficiary account extraction from NPCI files

### 4.3 Exception Handling Matrix
**Based on CBS-Switch-NPCI status combinations:**
- Success-Success-Success → Matched/No action
- Success-Success-Failed → Remitter Refund/Beneficiary Recovery
- Success-Failed-Success → Switch Update
- And other combinations as per document

## Phase 5: Reporting & Settlement

### 5.1 Enhanced Reports
**Matching Reports:**
- GL vs Switch - Matched (Inward/Outward)
- Switch vs Network - Matched (Inward/Outward)
- GL vs Network - Matched (Inward/Outward)

**Unmatched Reports with Ageing:**
- GL vs Switch - Unmatched (Inward/Outward)
- Switch vs Network - Unmatched (Inward/Outward)
- GL vs Network - Unmatched (Inward/Outward)

**Special Reports:**
- Hanging Transactions (Inward/Outward)

### 5.2 Settlement Processing
**NTSL Processing:**
- Verify summarized values against Raw files
- Generate settlement TTUMs
- Fund movement between internal and NPCI settlement accounts

### 5.3 Adjustment File Processing
**NPCI Bulk Upload Formats:**
- DRC (Debit Reversal Confirmation)
- RRC (Return Reversal Confirmation)
- TCC 102/103 files
- RET files
- Credit Adjustment files

## Phase 6: GL Justification & Dispute Management

### 6.1 GL Justification
**Status:** On hold (as per document)
**Future Implementation:**
- Variance analysis
- Bridge creation
- Proofing reports

### 6.2 Dispute Management
**Status:** On hold (as per document)
**Future Implementation:**
- Dispute workflow
- Arbitration handling
- Resolution tracking

## Implementation Priority

### High Priority (Phase 1-3)
1. Enhanced file validation with UPI-specific rules
2. UPI matching logic implementation
3. TTUM generation framework
4. Basic adjustment file processing

### Medium Priority (Phase 4-5)
1. Complete TTUM types implementation
2. Enhanced reporting with ageing
3. Settlement processing
4. File dashboard implementation

### Low Priority (Phase 6)
1. GL Justification features
2. Dispute Management system

## Technical Requirements

### Database Schema Extensions
- UPI-specific transaction tables
- TTUM templates and configurations
- Adjustment file tracking
- Settlement records

### API Extensions
- TTUM generation endpoints
- Adjustment file processing
- Settlement APIs
- Enhanced reporting APIs

### Configuration Management
- Matching parameter configurations
- GL account mappings
- File format specifications
- Cycle and schedule configurations

## File Format Specifications

### Required Files (3-way Recon)
**NPCI Files:**
- NPCI Raw (Inward/Outward) - 20 files/day
- NPCI Merchant (Inward/Outward) - 20 files/day
- NTSL - 20 files/day
- Adjustment Reports - 20 files/day

**Bank Files:**
- CBS GL (Inward/Outward) - 2 files/day
- Switch Log - 2 files/day

### Key Fields for Reconciliation
- UPI_Tran_ID
- RRN (Reference Number)
- Amount
- Tran_Date
- Response_Code (RC)
- Tran_Type (U2/U3)
- Account numbers
- PSP codes

## Testing Strategy

### Unit Testing
- Individual TTUM generation logic
- Matching algorithm validation
- File validation rules

### Integration Testing
- End-to-end reconciliation flow
- File processing pipelines
- Settlement calculations

### UAT Testing
- Real file processing
- TTUM accuracy validation
- Settlement verification

## Dependencies
- PGP decryption libraries (when implemented)
- Enhanced file parsing capabilities
- GL integration APIs
- Settlement system interfaces

## Risk Assessment
- Complex matching logic requires thorough testing
- TTUM accuracy critical for financial operations
- Settlement calculations must be 100% accurate
- File format changes from NPCI need handling

## Success Criteria
- All UPI-specific reconciliation scenarios handled
- TTUMs generated accurately for all exception cases
- Settlement processes automated
- Reports provide complete visibility
- System handles all required file types and volumes
