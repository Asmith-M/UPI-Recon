# IMPS Reconciliation Solution - BRD Amendment Guide

**Date:** December 04, 2025
**Document Reference:** IMPS - BRD.pdf
**Purpose:** To outline critical updates regarding Rollback granularity, Force Matching UI (LHS/RHS), AI/ML integration, and Risk Management capabilities.

---

## 1. Rollback Functionality (Significant Update)

**Current Reference:** Section 3.1.6 Rollback [cite: 529] currently limits rollback to "File upload rollback" only [cite: 532] and "available only for the latest file"[cite: 536].

**Requirement Change:** The system must support **Granular Rollback** at every stage of the process (Cycle-wise, Mid-recon, and Full Process).

**New Section Proposal: 3.1.6. Granular Rollback Mechanism**

The system shall provide a multi-level rollback mechanism to ensure data integrity during processing failures or operational errors.

### A. Step-by-Step Rollback
* **Stage 1: Ingestion Rollback:** If a file fails validation (format/checksum) during upload, the system must allow immediate rollback of that specific file without affecting previously uploaded files.
* **Stage 2: Mid-Recon Rollback:** If the reconciliation engine encounters a critical error (e.g., DB disconnection) *during* the matching process, the system must automatically roll back all uncommitted transactions to their "Unmatched" state to prevent data corruption.
* **Stage 3: Cycle-Wise Rollback:** As NPCI data arrives in 10 cycles[cite: 109], the user must be able to roll back a specific cycle (e.g., Cycle 3C) for re-processing, without needing to roll back the entire day's work.

### B. Accounting Rollback
* If a CBS Accounting File is generated but fails to upload to the Core Banking System (CBS), the user must have the option to "Rollback Voucher Generation." This resets the status of the included transactions from "Settled/Voucher Generated" back to "matched/pending" so the file can be regenerated.

---

## 2. Force Matching UI (LHS vs. RHS)

**Current Reference:** Section 3.1.4 Force Matching [cite: 510] describes manual matching and a zero-difference check [cite: 515] but does not define the User Interface layout.

**Requirement Change:** Explicitly define the UI layout using LHS (Bank) and RHS (Network) terminology.

**Updated Section Proposal: 3.1.4. Manual Force Matching (LHS vs. RHS)**

To facilitate complex manual reconciliation, the "Force Match" screen shall be divided into two distinct panels:

* **LHS (Left Hand Side) - Internal Records:**
    * This panel displays records from the **Bank's Systems** (CBS GL entries and Switch Logs).
    * Users can select multiple entries here (e.g., 1 Switch Success Log + 1 CBS Debit).
* **RHS (Right Hand Side) - External Records:**
    * This panel displays records from the **Network** (NPCI Raw and NTSL Files).
    * Users can select corresponding entries here (e.g., 1 NPCI Credit).

**Validation Logic:**
The system will strictly enforce the Zero-Difference Rule[cite: 514]. The "Match" button will remain disabled unless:
$$\sum (LHS\ Amount) - \sum (RHS\ Amount) = 0$$

---

## 3. Exception Handling (Process & Business)

**Current Reference:** The document details business logic exceptions (e.g., "CBS Exception Handling Scenario" [cite: 254]) extensively.

**Requirement Change:** Add **System Exception Handling** to support the new Rollback requirements.

**New Subsection: 3.2. Process Exception Handling**

In addition to transaction-level exceptions, the system must handle process-level exceptions:
* **SFTP Failures:** If the scheduler-based SFTP upload [cite: 128] fails mid-transfer, the system must alert the administrator and tag the file as "Partial/Corrupt" to prevent auto-recon initiation.
* **Duplicate Cycle Detection:** If a file for a cycle (e.g., 1C) is uploaded twice, the system must flag it immediately rather than attempting to process duplicate records.

---

## 4. GL Justification & Proofing

**Current Reference:** Section "Recon Statement (Outward/Remitter GL Proofing)" [cite: 298] and the provided table[cite: 307].

**Requirement Change:** Ensure the GL Proofing module supports "Day-Zero to Day-End" bridging.

**Update to Section 5.2.1 Reports:**
The **GL Justification Report** must explicitly link the Opening and Closing balances:
* **A. Opening Balance:** (Derived from Previous Day EOD).
* **B. Total Debits (CBS):** Sum of all outward postings.
* **C. Total Credits (CBS):** Sum of all returns/refunds.
* **D. Net Movement:** $(B - C)$.
* **E. Calculated Closing Balance:** $(A + D)$.
* **F. Actual System Closing Balance:** (Fetched via EOD Balance File [cite: 302]).
* **G. Unexplained Difference:** $(E - F)$. *Note: This must be zero.*

---

## 5. AI & ML Implementation (New Module)

**Current Reference:** Not present in existing document.
**Placement:** Insert as **Chapter 8**.

**New Chapter: 8. AI & Machine Learning Capabilities**

To enhance reconciliation rates beyond standard logic, the system will incorporate AI/ML modules:

### 8.1. Predictive Matching
* The system will use Machine Learning algorithms to analyze historical manual matches (Force Matches).
* It will identify patterns where standard parameters (RRN/Txn ID) are garbled or truncated but other attributes (Amount, Time window, Terminal ID) correlate strongly.
* The system will present these as "Suggested Matches" with a confidence score (e.g., 95% confidence), allowing the user to "Accept All" rather than manually searching.

### 8.2. Anomaly Detection
* The system will monitor settlement cycles for anomalies, such as:
    * Sudden spikes in "Response Code 91" (Timeout) compared to the 30-day moving average.
    * Unusual volume of "Force Un-match" actions [cite: 520] by a specific user.

---

## 6. Risk Management

**Current Reference:** Not present in existing document.
**Placement:** Insert as **Chapter 9**.

**New Chapter: 9. Risk Management & Controls**

### 9.1. Aging Analysis & Alerts
* The system must track the aging of unmatched entries in the Parking/Suspense GLs.
* **Alert Triggers:**
    * Items pending > T+3 days.
    * Accumulated unmatched amount exceeding defined thresholds (e.g., ₹10 Lakhs).

### 9.2. High-Value Transaction Controls
* **Dual Authorization:** Any "Force Match" or "Manual Adjustment" exceeding a configurable limit (e.g., ₹50,000) requires Checker approval[cite: 519].
* **Settlement Thresholds:** If the Net Settlement Amount in the NTSL file [cite: 118] deviates by >10% from the average of the last 7 days, the system should pause final accounting generation for manual review.

### 9.3. Audit Trail
* Every action, specifically "Force Un-match" [cite: 520] and "Rollback"[cite: 530], must be logged with: User ID, Timestamp, Action Type, and Pre/Post Data State.