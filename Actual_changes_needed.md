# Required Changes

## Modifications Requested by Them (Actual Required Changes)

1. Force Matching UI (Left Side vs. Right Side) — refer *Change_needed_by_them.md*.
2. Exception Handling (Process-Level and Business-Level) — refer *Change_needed_by_them.md*.
3. Rollback Functionality (Major Enhancement) — refer *Change_needed_by_them.md*.
4. Risk Management Improvements — refer *Change_needed_by_them.md*.
## Also refer *Change_needed_by_them.md* for addition changes.

---

# Prototype Fixes Needed

1. **Fix View Upload** — the system shows all files even when one or more files are missing. (Fixed)
2. **Fix the Recon Dashboard** — backend works, but the frontend does not display details. Reports and required items are missing, and the adjustment file download is not implemented. (Fixed)
3. **Enable All Report Downloads** — currently, only a few files are available for download.
4. **Add Date and Type Matching** in the Unmatched Dashboard. (Added)
5. **Add Cycle-Wise File Upload** (for NPCI files) in the File Upload module.(Added)
6. **Main Dashboard contains two sections:**

   * **Recon Dashboard** — fix graphs where arrows overlap in certain charts. Add additional comparison graph options. Fully utilize provided filters such as transaction category, date range, and transaction type.
   * **Today Break** — add graphs and display current day’s data. (Done)
7. **Integrate Loguru** in the backend for improved logging.
