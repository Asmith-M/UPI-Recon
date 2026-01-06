# UPI Recon Checklist Implementation

## ✅ UI / UX CONSISTENCY
- [x] Logo on every page (already done)
- [ ] Date selection on every page
- [ ] Update: Add shared layout/header component

## 📊 DASHBOARD & REPORTING
- [ ] Summary: In / Out values
- [ ] Check: Summary correctness
- [ ] Update: Separate Inflow / Outflow clearly
- [ ] Dashboard – Date-wise details
- [ ] Check: Date aggregation accuracy
- [ ] Update: Date-wise breakup, Today's break, Trend-wise view (graph)
- [ ] Recon dashboard – range selection
- [ ] Check: Missing date range selector
- [ ] Update: From–To date filter affecting all widgets

## 🔁 RECONCILIATION FEATURES
- [ ] Switch unmatched (toggle view)
- [ ] Check: Toggle exists / works
- [ ] Update: Quick switch between matched ↔ unmatched
- [ ] Force match – Date & PRN mandatory
- [ ] Check: Validation missing
- [ ] Update: Enforce Date + PRN before force match
- [ ] Parameters filter enhancement
- [ ] Check: Current filters limited
- [ ] Update filters for: Date, Amount, Transaction ID, RRN

## ⏪ ROLLBACK & DATA SAFETY
- [ ] Rollback – TTem also rollback
- [ ] Check: Partial rollback happening
- [ ] Update: Ensure TTem entries rollback together

## 🔐 ACCESS & CONTROL
- [ ] Disable feature (as per Asmith's instruction)
- [ ] Check: Feature still active
- [ ] Update: Disable at UI + backend level
- [ ] User management page (login control)
- [ ] Check: Admin capability missing
- [ ] Update: Create users, Assign roles, Enable / disable access
- [ ] login page with role based access

## Implementation Progress
1. [ ] Create Global Date Filter Component
2. [ ] Update Dashboard with Inflow/Outflow separation
3. [ ] Add date range selector to Recon Dashboard
4. [ ] Enhance Unmatched page with toggle and filters
5. [ ] Update Force Match with Date/PRN validation
6. [ ] Implement Role-Based Access
7. [ ] Create User Management page
8. [ ] Update Rollback logic for TTem entries
