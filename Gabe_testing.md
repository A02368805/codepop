# Gabe Testing - Bug Report Log

**Tester:** Gabriel Nielsen
**Date:** 2026-04-07
**Branch:** distributed-node-prep

## Stories Under Test

- Story 45 – Favorites
- Story 42 – Recommendations
- Story 34 – Revenue
- Story 2 – Supply levels
- Story 5 – CSV import
- Story 17 – Super admin
- Cross-role filtering
- Story 67 – Guest refund
- M6 – Mobile CSV upload

---

## Bugs Found

### Bug #1 — Favorites limited to pre-checkout only

**PAGE URL:** /orders (past orders screen)
**BUG DESCRIPTION:** Users cannot add a drink to favorites from the past orders screen — only pre-checkout.
**BUG TYPE:** UX / Missing Functionality
**CURRENT BEHAVIOR:** Favorite button is only available before placing an order (pre-checkout).
**EXPECTED BEHAVIOR:** Users should be able to mark a drink as a favorite from their past orders, since they may not know they like a drink until after trying it.
**STEPS TO REPRODUCE:**
1. Place an order for a drink.
2. Navigate to past orders screen.
3. Attempt to add the drink to favorites — no option available.

**ERROR MESSAGE:** N/A
**SCREENSHOT:** N/A
**NOTES:** Feature works correctly pre-checkout. This is an enhancement request — add a favorite button to past order items.

---

### Bug #2 — Supply deduction counts distinct drinks, not total quantity

**PAGE URL:** /inventory (supply levels)
**BUG DESCRIPTION:** When an order contains multiple drinks sharing a base ingredient, the supply level drops by the number of distinct drink types instead of total quantity ordered.
**BUG TYPE:** Logic / Calculation Error
**CURRENT BEHAVIOR:** Ordering 1 Diet Coke Cherry + 2 Diet Coke Lime reduces Diet Coke supply by 2 (number of distinct drinks) instead of 3 (total quantity).
**EXPECTED BEHAVIOR:** Supply should decrease by the total quantity of drinks ordered that use that ingredient (3 in this case).
**STEPS TO REPRODUCE:**
1. Note current Diet Coke supply level.
2. Place an order with 1 Diet Coke Cherry and 2 Diet Coke Lime.
3. Check Diet Coke supply level — it dropped by 2 instead of 3.

**ERROR MESSAGE:** N/A
**SCREENSHOT:** N/A
**NOTES:** The deduction logic appears to be counting distinct order line items rather than summing their quantities.

---

### Bug #3 — No guard preventing sale when ingredient quantity is 0

**PAGE URL:** /orders (order placement)
**BUG DESCRIPTION:** There may be no validation preventing a customer from ordering a drink when a required ingredient has 0 quantity in stock.
**BUG TYPE:** Validation / Business Logic (Needs Verification)
**CURRENT BEHAVIOR:** Unclear if a guard exists — needs verification that orders are blocked when supply is 0.
**EXPECTED BEHAVIOR:** System should prevent the sale and notify the customer when a required ingredient is out of stock.
**STEPS TO REPRODUCE:**
1. Set an ingredient's supply quantity to 0.
2. Attempt to order a drink that requires that ingredient.
3. Check if the order goes through or is blocked.

**ERROR MESSAGE:** N/A
**SCREENSHOT:** N/A
**NOTES:** Needs testing to confirm whether the guard exists. If not, this is a missing validation that should be added.

---

### Bug #4 — CSV import fails via web upload but parses correctly in shell

**PAGE URL:** /imports (CSV Import workspace)
**BUG DESCRIPTION:** Uploading a valid supply usage CSV through the web form results in "Store matching query does not exist" for every row, even though the same CSV parses successfully when run directly through the Django shell.
**BUG TYPE:** Bug / Data Processing
**CURRENT BEHAVIOR:** All rows fail with "Store matching query does not exist" when uploaded via the browser, despite store codes (C001, C002) existing in the database.
**EXPECTED BEHAVIOR:** The CSV should import successfully, matching rows to existing stores just as it does when parsed in the shell.
**STEPS TO REPRODUCE:**
1. Log in as super admin.
2. Navigate to the CSV Imports page.
3. Upload a valid supply usage CSV (with known-good store codes like C001, C002) using the "Import supply usage CSV" form.
3. All rows fail with "Store matching query does not exist."

**ERROR MESSAGE:** Row 2 — Store matching query does not exist. / Row 3 — Store matching query does not exist. / Row 4 — Store matching query does not exist.
**SCREENSHOT:** N/A
**NOTES:** The CSV was validated directly in the Django shell using `parse_supply_usage_csv()` and all 3 rows parsed successfully. The issue likely lies in the web upload path — possible causes include file encoding (BOM), the async `process_import_job_async` task running against a different DB context, or the `queue_import_job` flow losing/corrupting the CSV text.

---

### Bug #5 — No navigation back to Super Admin dashboard

**PAGE URL:** Any page after leaving the Super Admin dashboard
**BUG DESCRIPTION:** Once the super admin navigates away from their dashboard (e.g., to analytics, accounts, imports), there is no way to return to the Super Admin dashboard via the UI.
**BUG TYPE:** UX / Navigation
**CURRENT BEHAVIOR:** After clicking any link from the Super Admin dashboard (e.g., "Open analytics", "Review accounts"), there is no nav link or breadcrumb to return to the Super Admin dashboard.
**EXPECTED BEHAVIOR:** The site navigation should include a persistent link back to the Super Admin dashboard for users with the super_admin role.
**STEPS TO REPRODUCE:**
1. Log in as super admin.
2. View the Super Admin dashboard.
3. Click "Open analytics" or "Review accounts."
4. Attempt to navigate back to the Super Admin dashboard — no link available.

**ERROR MESSAGE:** N/A
**SCREENSHOT:** N/A
**NOTES:** User must manually type the URL or use browser back button. A "Dashboard" link should be added to the main nav for super_admin users.

---

### Bug #6 — Super Admin scope limited on distributed node setup

**PAGE URL:** Super Admin dashboard and related pages
**BUG DESCRIPTION:** On the DigitalOcean distributed deployment, the Super Admin dashboard only shows data for the local node's store(s), not system-wide data across all nodes.
**BUG TYPE:** Architecture / Distributed Data
**CURRENT BEHAVIOR:** Super Admin metrics (account counts, region comparison, audit logs, etc.) only reflect the local node's database. Stores, users, and operations on the other node are invisible.
**EXPECTED BEHAVIOR:** Super Admin should have a system-wide view aggregating data across all nodes — showing all stores, all regions, all users, and all operations regardless of which node they originated on.
**STEPS TO REPRODUCE:**
1. Log in as super admin on one node (e.g., store1-sf3).
2. View the Super Admin dashboard.
3. Observe that data only reflects the local node's stores/operations — other node's data is missing.

**ERROR MESSAGE:** N/A
**SCREENSHOT:** N/A
**NOTES:** Same distributed architecture issue as Bug #4. Each node has its own DB scoped to its own store. The Super Admin role needs a cross-node data aggregation layer — either a federated query to peer nodes' APIs or a central read-replica/sync that consolidates data for system-wide views.

---

### Bug #7 — Cross-role permission denied message uses unclear wording

**PAGE URL:** Any role-restricted page (e.g., ordering page accessed by manager)
**BUG DESCRIPTION:** When a user tries to access a page outside their role, the error message references "scopes" which is developer jargon, not user-friendly language.
**BUG TYPE:** UX / Copy
**CURRENT BEHAVIOR:** Permission denied message uses wording along the lines of "keeping scopes" or scope-related language.
**EXPECTED BEHAVIOR:** Message should say something clear like "You don't have access to this resource" or "This page is only available for customer accounts."
**STEPS TO REPRODUCE:**
1. Log in as a manager account.
2. Attempt to order a drink (customer-only flow).
3. Observe the permission denied message uses scope-related jargon.

**ERROR MESSAGE:** Scope-related wording (exact text TBD)
**SCREENSHOT:** N/A
**NOTES:** Cross-role filtering itself works correctly — manager is properly blocked from customer actions. This is purely a copy/UX cleanup. All permission denied messages across the app should be reviewed for user-friendly wording.

---

### Bug #8 — Guest order stuck, cannot complete due to locker pickup step

**PAGE URL:** /orders (guest order flow)
**BUG DESCRIPTION:** Guest orders never reach a completed state because the flow hangs waiting for a physical locker entry/pickup confirmation that cannot be fulfilled in the web app.
**BUG TYPE:** Workflow / Blocking
**CURRENT BEHAVIOR:** After placing a guest order, the order gets stuck at a locker pickup step. There is no way to simulate or bypass the physical locker confirmation, so the order never completes.
**EXPECTED BEHAVIOR:** There should be a way to complete the order — either a manual "confirm pickup" button for demo/testing purposes, or the locker step should be skippable when no physical hardware is connected.
**STEPS TO REPRODUCE:**
1. Place an order as a guest.
2. Order enters a pending/locker pickup state.
3. No way to confirm pickup or advance the order to "completed."

**ERROR MESSAGE:** N/A
**SCREENSHOT:** N/A
**NOTES:** This blocks testing of Story 67 (Guest refund) entirely — cannot test refund flow if orders never reach completed status. A demo/test mode bypass for the locker step would unblock both stories.

---

### Bug #9 — Mobile CSV upload page has poor responsive styling

**PAGE URL:** /imports (on mobile device)
**BUG DESCRIPTION:** The CSV import page is functionally accessible on mobile but the layout is badly broken.
**BUG TYPE:** UI / Responsive Design
**CURRENT BEHAVIOR:** Page has excessive scrolling, and the tab bar gets pushed off screen. Overall layout is not mobile-friendly.
**EXPECTED BEHAVIOR:** Import page should have a responsive layout — forms should stack cleanly, tab bar should remain visible/accessible, and content should fit within the viewport without excessive scrolling.
**STEPS TO REPRODUCE:**
1. Open the imports page on a mobile device (or browser mobile emulation).
2. Observe endless scrolling and tab bar pushed off screen.

**ERROR MESSAGE:** N/A
**SCREENSHOT:** N/A
**NOTES:** The upload functionality itself works — this is purely a styling/responsive issue. Additionally, the same distributed node store scope issue from Bug #4 and #6 will likely affect mobile CSV uploads as well (CSV referencing stores not on the local node will fail).

---

**DISTRIBUTED NODE CONTEXT:** The DigitalOcean deployment has two independent droplets (store1-sf3 @ 134.199.222.195, store2-sf3 @ 64.227.100.242), each scoped to its own store with its own database. This means a node may only have its own store's data locally and would not recognize store codes belonging to other nodes. This is likely the root cause — a CSV referencing C001, C002, etc. will fail on a node that only knows about its own store. Each node should be aware of all stores in the system (store registry) but only hold operational data for its own store. If a CSV references a store on another node, the system should be able to connect to that node's API to validate/read the data rather than failing outright. This is a broader architectural consideration for the distributed setup.
