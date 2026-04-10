# Bugs Found During Testing

## Bug 1: No Display of Current Store/Region in Distributed Mode
**REPORTER:** Curt
**PAGE URL:** All pages

**BUG DESCRIPTION:** In distributed mode, there's no visual indication of which store or region the user is currently on. A user accessing localhost:8001 (Chicago) vs localhost:8002 (NJ) has no way to know which instance they're logged into.

**BUG TYPE:** Missing Information / Distributed Architecture

**CURRENT BEHAVIOR:** No store/region indicator in navbar or header. Users can't tell which node they're on.

**EXPECTED BEHAVIOR:** Navbar or header should clearly show "Chicago Store (A001)" or "Region A: Chicago" so users know which instance they're accessing.

**STEPS TO REPRODUCE:**
1. Go to http://localhost:8001/ (log in as manager.a001@floatstack.local)
2. Notice no indicator of "Chicago" or "Store A001"
3. Go to http://localhost:8002/ (if running multi-node)
4. Notice same navbar—can't tell you're in a different region

**ERROR MESSAGE:** None (missing information)

**SCREENSHOT:** N/A

**NOTES:** 
- **Severity:** Medium
- **Priority:** P2 (distributed mode only, not critical for single-instance)
- Quick fix: Add store/region name to navbar
- Helps prevent confusion when managing multiple instances
- Critical for distributed testing and multi-region deployments

---

## Bug 2: Stores from Other Nodes Not Shown in Pickup Locations
**REPORTER:** Curt
**PAGE URL:** /stores/

**BUG DESCRIPTION:** In distributed mode, users on store-a instance can only see store A001. Stores B001, C001 from other nodes are not available. This breaks Story 59 (manual store selection) in distributed systems.

**BUG TYPE:** Feature Not Implemented (distributed architecture issue)

**CURRENT BEHAVIOR:** Pickup locations page only shows local store; peer stores are not fetched.

**EXPECTED BEHAVIOR:** All stores from all nodes should be listed so users can pick any store to order from, regardless of which instance they're on.

**STEPS TO REPRODUCE:**
1. Run distributed setup: `docker compose -f docker-compose.multi.yml up -d --profile store-b --profile store-c`
2. Go to http://localhost:8001/stores/
3. Scroll to "All Locations"
4. Notice only Chicago Loop (A001) appears, no other regional stores

**ERROR MESSAGE:** None (missing feature—no peer stores shown)

**SCREENSHOT:** N/A

**NOTES:**
- **Severity:** Critical
- **Priority:** P1 (blocks Story 59 in distributed mode)
- Causes complete failure of multi-store selection testing
- Requires implementing `StoreApiView` and updating `_get_all_stores()` to fetch from peers
- See notes in bootstrap_demo_data.py for attempted fix

---

## Bug 3: No Confirmation Before Progressing Order Status
**REPORTER:** Curt
**PAGE URL:** /orders/

**BUG DESCRIPTION:** Clicking "Preparing", "Ready", or "Picked up" buttons on the order queue immediately changes status with no confirmation dialog or visual feedback. Too easy to accidentally advance an order.

**BUG TYPE:** UX / Data Loss Risk

**CURRENT BEHAVIOR:** Single click instantly transitions order to next status. Page updates via HTMX.

**EXPECTED BEHAVIOR:** Show a confirmation dialog ("Mark as ready? This can't be undone.") before confirming the status change. Or show a highlighted button state with a tooltip explaining what will happen.

**STEPS TO REPRODUCE:**
1. Log in as manager.a001@floatstack.local
2. Go to /orders/
3. Find a QUEUED order
4. Click "Preparing" button
5. Status instantly changes to PREPARING with no warning

**ERROR MESSAGE:** None (immediate state change)

**SCREENSHOT:** N/A

**NOTES:**
- **Severity:** High
- **Priority:** P1 (data integrity risk)
- Easy to accidentally mark orders as ready when they're still being prepared
- Requires adding confirmation modal or button state before action
- Should add undo/recover mechanism if possible

---

## Bug 4: Maintenance Page Has No Margins Between Sections
**REPORTER:** Curt
**PAGE URL:** /maintenance/

**BUG DESCRIPTION:** The three main sections (Urgency Queue, Route-Aware Queue, Repair Assignments) have no vertical spacing/margins between them, making them visually run together.

**BUG TYPE:** UI/Layout

**CURRENT BEHAVIOR:** Sections directly adjacent with no padding or visual separation.

**EXPECTED BEHAVIOR:** Each section should have clear top/bottom margins (e.g., 2rem) for visual hierarchy and readability.

**STEPS TO REPRODUCE:**
1. Log in as repair.north@floatstack.local
2. Go to /maintenance/
3. Observe sections appear cramped together

**ERROR MESSAGE:** None (layout issue)

**SCREENSHOT:** N/A

**NOTES:**
- **Severity:** Low
- **Priority:** P3 (cosmetic, doesn't block functionality)
- Quick CSS fix: add `margin-top: 2rem;` to `.panel` sections
- Affects readability but not usability

---

## Bug 5: Machine Priority Score Is Confusing to Users
**REPORTER:** Curt
**PAGE URL:** /maintenance/

**BUG DESCRIPTION:** Priority column shows numeric scores (986.00, 1595.00) with no explanation. Users don't know if higher is worse, what the range is, or what they mean.

**BUG TYPE:** UX / Unclear Data Presentation

**CURRENT BEHAVIOR:** Priority shows as decimal numbers calculated from days-in-status and machine status.

**EXPECTED BEHAVIOR:** Either:
- Show severity labels (CRITICAL, HIGH, MEDIUM, LOW) instead of numbers
- Add a tooltip/legend explaining the score (e.g., "Priority: 1595 (machine in error for 7+ days)")
- Color-code by priority level

**STEPS TO REPRODUCE:**
1. Go to /maintenance/
2. Look at "Priority" column in Urgency Queue
3. Try to understand what "986.00" or "1595.00" means

**ERROR MESSAGE:** None (user confusion—no error shown)

**SCREENSHOT:** N/A

**NOTES:**
- **Severity:** Medium
- **Priority:** P2 (affects user understanding but not action)
- Users don't know which machine to fix first
- Recommend adding a legend: "Priority: Calculated from machine age + status severity"
- Or convert to severity labels (CRITICAL=red, HIGH=orange, MEDIUM=yellow, LOW=blue)
- Priority calculated in `calculate_machine_priority()` in maintenance/services.py

---

## Bug 6: Machine Repair UI Is Too Narrow and Long
**REPORTER:** Curt
**PAGE URL:** /maintenance/ (urgency queue table)

**BUG DESCRIPTION:** The table displaying machines is extremely narrow (columns packed tight) and very long (scrolls forever). Text is cramped and hard to read.

**BUG TYPE:** UI/Layout

**CURRENT BEHAVIOR:** Urgency queue table has 8 columns (Store, Machine, Status, Assignment, Route, Priority, Priority Reason, Actions) all crammed into viewport width.

**EXPECTED BEHAVIOR:** Either:
- Make the table wider (full viewport or scrollable horizontally)
- Reorganize into a card layout instead of table
- Collapse/expand machine details to reduce vertical length

**STEPS TO REPRODUCE:**
1. Go to /maintenance/
2. Try to read machine names, statuses, and reasons in the Urgency Queue table
3. Observe text is cut off and columns are too narrow

**ERROR MESSAGE:** None (layout issue—text cut off)

**SCREENSHOT:** N/A

**NOTES:**
- **Severity:** High
- **Priority:** P1 (blocks readability and usability of maintenance page)
- 8 columns crammed into narrow viewport
- Recommend: convert table to card layout or implement horizontal scroll
- Alternative: hide "Route" and "Priority Reason" behind expandable row details

---

## Bug 7: Clicking "Start Repair" Scrolls Page to Bottom
**REPORTERS:** Curt, Matthew
**PAGE URL:** /maintenance/

**BUG DESCRIPTION:** When clicking "Start", "Close", or other assignment action buttons, the page automatically scrolls to the bottom instead of staying in view. Disorienting and requires scrolling back up.

**BUG TYPE:** UX / Navigation

**CURRENT BEHAVIOR:** HTMX response replaces section and auto-scrolls to bottom of page.

**EXPECTED BEHAVIOR:** Page should stay at same scroll position or scroll smoothly to the updated assignment card.

**STEPS TO REPRODUCE:**
1. Go to /maintenance/
2. Scroll to "Repair Assignments" section
3. Click "Start" button on an assignment
4. Page jumps to bottom instead of showing updated assignment

**ERROR MESSAGE:** None (navigation issue—unwanted scroll)

**SCREENSHOT:** N/A

**NOTES:**
- **Severity:** Medium
- **Priority:** P2 (annoys users but doesn't break functionality)
- HTMX likely using default scroll behavior after swap
- Fix: Add HTMX config to preserve scroll position or scroll to updated element
- See: `hx-swap` documentation for "scroll:" modifier

---

## Bug 8: Inventory Search Requires Enter Key
**REPORTER:** Curt
**PAGE URL:** /inventory/

**BUG DESCRIPTION:** Inventory search only filters when you press Enter. Modern UX expects live search as you type.

**BUG TYPE:** UX / Discoverability

**CURRENT BEHAVIOR:** Type in search box, items don't filter until you hit Enter.

**EXPECTED BEHAVIOR:** Filter items as you type (debounced to avoid excessive requests).

**STEPS TO REPRODUCE:**
1. Go to /inventory/
2. Start typing in search box (e.g., "syrup")
3. Notice items don't filter until you press Enter

**ERROR MESSAGE:** None (silent—no feedback while typing)

**SCREENSHOT:** N/A

**NOTES:**
- **Severity:** Low
- **Priority:** P3 (UX improvement, not a blocker)
- Modern expectation is live search
- Fix: Add HTMX `hx-trigger="keyup changed delay:500ms"` to search input
- Add debounce to prevent excessive requests

---

## Bug 9: Inventory Adjust Shows No Error Message for Missing Note
**REPORTER:** Curt
**PAGE URL:** /inventory/

**BUG DESCRIPTION:** When adjusting inventory without a reason/note, form silently fails with no visible error message to the user. The form just doesn't submit.

**BUG TYPE:** Form UX / Error Handling

**CURRENT BEHAVIOR:** Form validation requires a reason, but error message doesn't display to user.

**EXPECTED BEHAVIOR:** Show inline error message: "Provide a reason for this adjustment" under the reason field.

**STEPS TO REPRODUCE:**
1. Go to /inventory/
2. Click adjust on any item
3. Enter quantity (e.g., 10)
4. Leave reason field blank
5. Click submit
6. Form doesn't submit with no visible error

**ERROR MESSAGE:** "Provide a reason for the inventory adjustment." (validation exists but not shown to user)

**SCREENSHOT:** N/A

**NOTES:**
- **Severity:** High
- **Priority:** P1 (blocks user from adjusting inventory)
- Form validation works server-side but error isn't rendered in HTMX response
- Fix: Ensure form errors display in `/inventory/partials/balance_row.html`
- Check `InventoryAdjustView` POST response rendering
- Users need immediate feedback on why adjustment failed

---

## Bug 10: Mobile Navbar Is Too Wide and Not Responsive
**REPORTERS:** Curt, Matthew, Brock, Braxton, Peyton
**PAGE URL:** All pages (responsive)

**BUG DESCRIPTION:** On mobile screens, the navigation bar takes up too much horizontal space, pushing content off-screen or wrapping awkwardly. Navigation is inconsistent across different screens and doesn't collapse to hamburger menu.

**BUG TYPE:** Responsive Design / Mobile UX / Navigation

**CURRENT BEHAVIOR:** 
- Navbar doesn't adapt properly to mobile widths (< 600px)
- Navigation affordances differ by screen
- Admin and manager dashboards may not include bottom nav
- Bottom-fixed navigation may overlap content without proper spacing
- Nav bar extends too far horizontally and compresses main content
- Sub nav bar doesn't stay with page on mobile like it does on desktop

**EXPECTED BEHAVIOR:** 
- Navbar should collapse to hamburger menu on mobile
- Stack vertically when open
- Not exceed viewport width
- Predictable navigation model across all screens
- Adequate bottom spacing so content is not hidden behind nav bar
- Responsive hamburger menu that closes/opens

**STEPS TO REPRODUCE:**
1. Open DevTools (F12)
2. Toggle device toolbar (iPhone SE or similar, ~375px width)
3. Navigate to any page (especially manager dashboard)
4. Observe navbar is too wide for screen, content wraps awkwardly
5. Check if nav remains available on all screens
6. Scroll to bottom of long pages and check if content is obscured
7. Test on mobile device or emulator

**ERROR MESSAGE:** None (responsive design failure)

**SCREENSHOT:** N/A

**NOTES:**
- **Severity:** High
- **Priority:** P2 (mobile usability issue, not critical for current testing)
- Navbar needs hamburger menu on mobile breakpoint (~768px and below)
- Check base.html and CSS media queries
- Blocks full mobile testing of features
- Navigation should be consistent across all screen types
- Should verify in Expo/emulator and real devices during M4/M5 testing

---

## Bug 11: /orders/checkout/ Missing Client-Side Form Validation
**REPORTER:** Curt
**PAGE URL:** /orders/checkout/

**BUG DESCRIPTION:** Form fields don't validate on blur/change, only on submit. Users don't know if their email/phone is invalid until they try to submit.

**BUG TYPE:** UX / Form Validation

**CURRENT BEHAVIOR:** Form only validates server-side on POST.

**EXPECTED BEHAVIOR:** Add client-side validation:
- Email field: validate on blur (basic email regex)
- Phone field: validate on blur (10 digits)
- Name field: validate on blur (not empty)
- Show inline error messages immediately

**STEPS TO REPRODUCE:**
1. Go to /orders/checkout/
2. Enter invalid email (e.g., "notanemail")
3. Tab to next field
4. No error message until you submit the form

**ERROR MESSAGE:** Server-side validation error shown only on form submission

**SCREENSHOT:** N/A

**NOTES:**
- **Severity:** Low
- **Priority:** P3 (UX improvement, server validation still works)
- Add HTML5 form validation attributes: `type="email"`, `required`, pattern checks
- Consider adding JavaScript blur handlers for immediate feedback
- Doesn't block order placement, just poor UX

---

## Bug 12: Form Validation Not Separated by Field
**REPORTER:** Curt
**PAGE URL:** Multiple pages (forms throughout app)

**BUG DESCRIPTION:** Form validation shows a single error summary at top, not field-specific errors. Users can't tell which field is wrong.

**BUG TYPE:** Form UX

**CURRENT BEHAVIOR:** All errors shown in one block at the top of the form.

**EXPECTED BEHAVIOR:** Show errors inline under each field (red text, error icon, etc.)

**STEPS TO REPRODUCE:**
1. Fill out any form with multiple required fields
2. Submit with some fields blank or invalid
3. Errors appear at top, not next to the problematic fields

**ERROR MESSAGE:** Error summary shown at top of form, e.g. "This field is required."

**SCREENSHOT:** N/A

**NOTES:**
- **Severity:** Low
- **Priority:** P3 (server validation works, UX could be better)
- Users must scroll up to see error after scrolling down to submit
- Fix: Render errors inline with each field in templates
- Check form rendering in `form.errors` and `field.errors` in templates
- Doesn't block functionality but hurts user experience

---

## Bug 13: Inventory Deduction Logic Incorrect - Multiple Issues
**REPORTERS:** Gabe, Brock
**PAGE URL:** /inventory/ (supply levels)

**BUG DESCRIPTION:** 
- When an order contains multiple drinks sharing a base ingredient, the supply level drops by the number of distinct drink types instead of total quantity ordered.
- When customer adds multiple quantity of same drink to cart and completes order, only 1 of each ingredient is subtracted instead of the full quantity.

**BUG TYPE:** Logic / Calculation Error

**CURRENT BEHAVIOR:** 
- Ordering 1 Diet Coke Cherry + 2 Diet Coke Lime reduces Diet Coke supply by 2 (number of distinct drinks) instead of 3 (total quantity).
- Ordering 12 of the same drink only subtracts 1 of each ingredient instead of 12.

**EXPECTED BEHAVIOR:** Supply should decrease by the total quantity of drinks ordered that use that ingredient, accounting for both the number of distinct drink types AND the quantity of each type.

**STEPS TO REPRODUCE:**
1. Note current Diet Coke supply level.
2. Place an order with 1 Diet Coke Cherry and 2 Diet Coke Lime.
3. Check Diet Coke supply level — it dropped by 2 instead of 3.

OR:

1. Order 12 of the same drink and add them to cart.
2. Complete the order and have it picked up.
3. Check inventory and see that only 1 of each ingredient was subtracted instead of 12.

**ERROR MESSAGE:** N/A

**SCREENSHOT:** N/A

**NOTES:** 
- **Severity:** High
- **Priority:** P1 (critical inventory leak)
- The deduction logic appears to be counting distinct order line items rather than summing their quantities
- This causes a huge inventory leak and can lead to significant issues with inventory management and order fulfillment
- Check order processing logic - likely counting drinks instead of quantities

---

## Bug 14: No Guard Preventing Sale When Ingredient Quantity Is 0
**REPORTER:** Gabe
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

**NOTES:** 
- Needs testing to confirm whether the guard exists. If not, this is a missing validation that should be added.

---

## Bug 15: CSV Import Fails Due to Store/Date Format Issues
**REPORTERS:** Gabe, Brock
**PAGE URL:** /imports (CSV Import workspace)

**BUG DESCRIPTION:** CSV imports fail with different errors depending on context:
1. Uploading supply usage CSV through web form results in "Store matching query does not exist" for every row
2. Uploading inventory/maintenance CSV fails with invalid date format errors

**BUG TYPE:** Bug / Data Processing

**CURRENT BEHAVIOR:** 
- All rows fail with "Store matching query does not exist" when uploaded via the browser, despite store codes existing
- Date parsing fails when CSV contains dates in M/D/YY format (e.g., '5/18/26')
- Maintenance CSV header parsing fails, treating comma-separated headers as multiple headers

**EXPECTED BEHAVIOR:** 
- CSV should import successfully, matching rows to existing stores
- Date parser should accept common date formats (M/D/YY, YYYY-MM-DD, etc.)
- CSV headers should be parsed correctly regardless of formatting

**STEPS TO REPRODUCE (Supply Usage):**
1. Log in as super admin.
2. Navigate to the CSV Imports page.
3. Upload a valid supply usage CSV with known-good store codes (C001, C002).
4. All rows fail with "Store matching query does not exist."

**STEPS TO REPRODUCE (Dates/Headers):**
1. Navigate to imports page.
2. Attempt to upload a CSV file with dates in M/D/YY format.
3. Observe error: "Invalid isoformat string: '5/18/26'"
4. For maintenance CSV with comma-separated headers, observe: "Expected headers ['store_address', 'machine_type_code'...] but received ['store_address,machine_type_code'...]"

**ERROR MESSAGES:** 
- "Store matching query does not exist"
- "Invalid isoformat string: '5/18/26'"
- "Expected headers [...] but received [...]"
- "MachineType matching query does not exist"

**SCREENSHOT:** N/A

**NOTES:** 
- **Severity:** High
- **Priority:** P1 (blocks critical import feature)
- The CSV was validated directly in Django shell using `parse_supply_usage_csv()` and parsed successfully, suggesting issue is in web upload path
- Possible causes: file encoding (BOM), async `process_import_job_async` task running against different DB context, `queue_import_job` flow losing/corrupting CSV text
- Date parser needs to accept M/D/YY format in addition to ISO format
- CSV header parsing may need to handle different delimiters/encodings
- Each node in distributed setup may only have its own store's data, causing store lookup to fail for other stores
- Distributed Node Context: Node may only recognize stores in its own database

---

## Bug 16: No Navigation Back to Super Admin Dashboard
**REPORTER:** Gabe
**PAGE URL:** Any page after leaving the Super Admin dashboard

**BUG DESCRIPTION:** Once the super admin navigates away from their dashboard (e.g., to analytics, accounts, imports), there is no way to return to the Super Admin dashboard via the UI.

**BUG TYPE:** UX / Navigation

**CURRENT BEHAVIOR:** After clicking any link from the Super Admin dashboard, there is no nav link or breadcrumb to return to the Super Admin dashboard.

**EXPECTED BEHAVIOR:** The site navigation should include a persistent link back to the Super Admin dashboard for users with the super_admin role.

**STEPS TO REPRODUCE:**
1. Log in as super admin.
2. View the Super Admin dashboard.
3. Click "Open analytics" or "Review accounts."
4. Attempt to navigate back to the Super Admin dashboard — no link available.

**ERROR MESSAGE:** N/A

**SCREENSHOT:** N/A

**NOTES:** 
- User must manually type the URL or use browser back button
- A "Dashboard" link should be added to the main nav for super_admin users

---

## Bug 17: Super Admin Scope Limited on Distributed Node Setup
**REPORTER:** Gabe
**PAGE URL:** Super Admin dashboard and related pages

**BUG DESCRIPTION:** On distributed deployment, the Super Admin dashboard only shows data for the local node's store(s), not system-wide data across all nodes.

**BUG TYPE:** Architecture / Distributed Data

**CURRENT BEHAVIOR:** Super Admin metrics only reflect the local node's database. Stores, users, and operations on other nodes are invisible.

**EXPECTED BEHAVIOR:** Super Admin should have a system-wide view aggregating data across all nodes — showing all stores, all regions, all users, and all operations regardless of which node they originated on.

**STEPS TO REPRODUCE:**
1. Log in as super admin on one node.
2. View the Super Admin dashboard.
3. Observe that data only reflects the local node's stores/operations.

**ERROR MESSAGE:** N/A

**SCREENSHOT:** N/A

**NOTES:** 
- Same distributed architecture issue as CSV imports
- Each node has its own DB scoped to its own store
- Super Admin role needs a cross-node data aggregation layer
- Either federated query to peer nodes' APIs or central read-replica/sync needed
- Distributed Node Context: Store1-sf3 @ 134.199.222.195, Store2-sf3 @ 64.227.100.242

---

## Bug 18: Cross-Role Permission Denied Message Uses Unclear Wording
**REPORTER:** Gabe
**PAGE URL:** Any role-restricted page (e.g., ordering page accessed by manager)

**BUG DESCRIPTION:** When a user tries to access a page outside their role, the error message references "scopes" which is developer jargon, not user-friendly language.

**BUG TYPE:** UX / Copy

**CURRENT BEHAVIOR:** Permission denied message uses scope-related language that users don't understand.

**EXPECTED BEHAVIOR:** Message should say something clear like "You don't have access to this resource" or "This page is only available for customer accounts."

**STEPS TO REPRODUCE:**
1. Log in as a manager account.
2. Attempt to order a drink (customer-only flow).
3. Observe the permission denied message uses scope-related jargon.

**ERROR MESSAGE:** Scope-related wording

**SCREENSHOT:** N/A

**NOTES:** 
- Cross-role filtering itself works correctly — manager is properly blocked from customer actions
- This is purely a copy/UX cleanup
- All permission denied messages across the app should be reviewed for user-friendly wording

---

## Bug 19: Guest Order Stuck - Cannot Complete Due to Locker Pickup Step
**REPORTER:** Gabe
**PAGE URL:** /orders (guest order flow)

**BUG DESCRIPTION:** Guest orders never reach a completed state because the flow hangs waiting for a physical locker entry/pickup confirmation that cannot be fulfilled in the web app.

**BUG TYPE:** Workflow / Blocking

**CURRENT BEHAVIOR:** After placing a guest order, the order gets stuck at a locker pickup step with no way to advance.

**EXPECTED BEHAVIOR:** There should be a way to complete the order — either a manual "confirm pickup" button for demo/testing purposes, or the locker step should be skippable when no physical hardware is connected.

**STEPS TO REPRODUCE:**
1. Place an order as a guest.
2. Order enters a pending/locker pickup state.
3. No way to confirm pickup or advance the order to "completed."

**ERROR MESSAGE:** N/A

**SCREENSHOT:** N/A

**NOTES:** 
- **Severity:** High
- **Priority:** P1 (test blocker)
- Blocks testing of Story 67 (Guest refund) entirely — cannot test refund flow if orders never reach completed status
- A demo/test mode bypass for the locker step would unblock both stories

---

## Bug 20: Mobile CSV Upload Page Has Poor Responsive Styling
**REPORTER:** Gabe
**PAGE URL:** /imports (on mobile device)

**BUG DESCRIPTION:** The CSV import page is functionally accessible on mobile but the layout is badly broken.

**BUG TYPE:** UI / Responsive Design

**CURRENT BEHAVIOR:** Page has excessive scrolling, and the tab bar gets pushed off screen. Overall layout is not mobile-friendly.

**EXPECTED BEHAVIOR:** Import page should have a responsive layout — forms should stack cleanly, tab bar should remain visible/accessible, and content should fit within the viewport without excessive scrolling.

**STEPS TO REPRODUCE:**
1. Open the imports page on a mobile device or browser mobile emulation.
2. Observe endless scrolling and tab bar pushed off screen.

**ERROR MESSAGE:** N/A

**SCREENSHOT:** N/A

**NOTES:** 
- The upload functionality itself works — this is purely a styling/responsive issue
- Same distributed node store scope issue will likely affect mobile CSV uploads
- CSV referencing stores not on the local node will fail

---

## Bug 21: AI-Generated Drink Result Missing Buy/Add-to-Cart Action
**REPORTER:** Matthew
**PAGE URL:** /orders/menu/C001/ai/

**BUG DESCRIPTION:** AI-generated drink result does not expose a visible buy/add-to-cart action.

**BUG TYPE:** Functional UI bug

**CURRENT BEHAVIOR:** After entering an AI drink prompt and getting a generated drink, the purchase button is not visible or clickable due to broken layout.

**EXPECTED BEHAVIOR:** A clear Buy or Add to Cart button should be visible and actionable immediately after AI generation.

**STEPS TO REPRODUCE:**
1. Log in as Customer account 2 (account.river@floatstack.local).
2. Open AI drink prompt flow and generate a drink.
3. Try to buy/add generated drink to cart.

**ERROR MESSAGE:** None shown.

**SCREENSHOT:** Pending.

**NOTES:** 
- Story 46 and 47
- Suggested severity: High (blocks AI ordering path)

---

## Bug 22: Manager Queue Interaction - Only Name Link Clickable
**REPORTER:** Matthew
**PAGE URL:** /orders/

**BUG DESCRIPTION:** Manager queue interaction requires clicking only the name link; full card/row is not clickable and workflow clarity is poor.

**BUG TYPE:** UX and Interaction

**CURRENT BEHAVIOR:** Only order name link is clickable for progression context; clicking broader card/row does nothing.

**EXPECTED BEHAVIOR:** Entire order card/row should be clickable with clearer stage-action affordances.

**STEPS TO REPRODUCE:**
1. Log in as manager (manager.c001@floatstack.local).
2. Open order queue.
3. Try clicking different parts of an order card/row.

**ERROR MESSAGE:** None shown.

**SCREENSHOT:** Pending.

**NOTES:** 
- Manager order queue new scope
- Suggested severity: Medium

---

## Bug 23: Inventory Adjustment Increments Use Wrong Step Size
**REPORTER:** Matthew
**PAGE URL:** /inventory/

**BUG DESCRIPTION:** Inventory adjustment increments use 0.01 for items that should use whole-number increments.

**BUG TYPE:** Functional data-entry behavior

**CURRENT BEHAVIOR:** Quantity controls increment by 0.01 regardless of item UoM expectations.

**EXPECTED BEHAVIOR:** Increment step should respect product UoM (whole-number steps for discrete items, decimal where appropriate).

**STEPS TO REPRODUCE:**
1. Log in as manager and open inventory.
2. Select an item expected to use whole-unit counts.
3. Use adjust control and observe 0.01 stepping.

**ERROR MESSAGE:** None shown.

**SCREENSHOT:** Pending.

**NOTES:** 
- Story 32
- Suggested severity: Medium

---

## Bug 24: Inventory Adjustment Does Not Immediately Update Quantity
**REPORTER:** Matthew
**PAGE URL:** /inventory/

**BUG DESCRIPTION:** Adjustment behavior does not match physical count correction expectation.

**BUG TYPE:** Functional workflow ambiguity

**CURRENT BEHAVIOR:** Submitted adjustment does not appear to immediately update visible quantity in the tested flow.

**EXPECTED BEHAVIOR:** If this is physical count correction, quantity should update immediately and clearly.

**STEPS TO REPRODUCE:**
1. Open inventory adjustment for an item.
2. Submit a physical count correction value.
3. Observe that on-hand value does not visibly reflect expected update in flow.

**ERROR MESSAGE:** None shown.

**SCREENSHOT:** Pending.

**NOTES:** 
- Story 32
- Suggested severity: High

---

## Bug 25: Inventory Adjustment Action Appears Not to Apply at All
**REPORTER:** Matthew
**PAGE URL:** /inventory/

**BUG DESCRIPTION:** Adjust action appears not to apply at all.

**BUG TYPE:** Functional failure

**CURRENT BEHAVIOR:** Tester cannot get adjustment to change inventory values.

**EXPECTED BEHAVIOR:** Adjustment should persist value changes or show clear validation/error feedback.

**STEPS TO REPRODUCE:**
1. Log in as manager and go to inventory.
2. Perform valid quantity adjustment and submit.
3. Verify values do not change as expected.

**ERROR MESSAGE:** None shown.

**SCREENSHOT:** Pending.

**NOTES:** 
- Story 33 path validation impacted
- Suggested severity: High

---

## Bug 26: Store Selection Missing During Drink Customization
**REPORTER:** Brock
**PAGE URL:** http://134.199.222.195:8000/orders/menu/A001/(drink-name)/ and /orders/cart/

**BUG DESCRIPTION:** Cannot change store while on drink customization page; can only order from Chicago store from main page.

**BUG TYPE:** Routes / Missing Functionality

**CURRENT BEHAVIOR:** No option to select a different store while customizing a drink.

**EXPECTED BEHAVIOR:** Have an option to select the store and stay on the drink customization page.

**STEPS TO REPRODUCE:**
1. Go to main home page (signed out)
2. Click on any drink to customize
3. Try to change the store but there is no option to do so

**ERROR MESSAGE:** N/A

**SCREENSHOT:** N/A

**NOTES:** 
- Routes issue - need to add a route to change the store while customizing the drink

---

## Bug 27: Customized Drink Name Doesn't Reflect Customizations in Cart
**REPORTER:** Brock
**PAGE URL:** http://134.199.222.195:8000/orders/cart/

**BUG DESCRIPTION:** After customizing a drink and adding to cart, it keeps the same name as the original drink, which is confusing when multiple customized drinks are in the cart.

**BUG TYPE:** UI / Functionality

**CURRENT BEHAVIOR:** When adding a customized drink to cart, it keeps the original drink name even if base and toppings are completely changed.

**EXPECTED BEHAVIOR:** Name in cart should reflect the customizations made to the drink, either by adding a unique identifier or by changing the name to reflect the customizations (base + toppings).

**STEPS TO REPRODUCE:**
1. Go to main home page (signed out)
2. Click on any drink to customize
3. Customize the drink (change the base, add toppings, etc.)
4. Click on "add to cart"
5. Go to cart page and see that the drink name does not change to reflect the customizations

**ERROR MESSAGE:** N/A

**SCREENSHOT:** N/A

**NOTES:** 
- Not a logic/breaking bug but should be fixed to improve UX
- Avoids confusion when multiple customized drinks are in the cart
- Could add unique identifier or dynamic name based on customizations

---

## Bug 28: Import History Window Not Scrollable
**REPORTER:** Brock
**PAGE URL:** http://127.0.0.1:8000/imports/

**BUG DESCRIPTION:** Window of import history is not scrollable, making it difficult to view all imported items.

**BUG TYPE:** UI

**CURRENT BEHAVIOR:** The import history window is not scrollable.

**EXPECTED BEHAVIOR:** The import history window should be scrollable and include a button to open the full history in a new page.

**STEPS TO REPRODUCE:**
1. Navigate to the import history page.
2. Attempt to scroll through the import history.
3. Notice that the window is not scrollable.

**ERROR MESSAGE:** N/A

**SCREENSHOT:** N/A

**NOTES:** 
- This is a UI issue that affects the usability of the import history feature
- Adding a scroll bar and a button to view the full history would enhance UX

---

## Bug 29: Analytics Page Missing Search Bar for Orders
**REPORTER:** Brock
**PAGE URL:** http://134.199.222.195:8000/analytics/

**BUG DESCRIPTION:** Analytics page lacks a search bar to search for specific orders.

**BUG TYPE:** UI / Functionality

**CURRENT BEHAVIOR:** The analytics page does not have a search bar to search for specific orders.

**EXPECTED BEHAVIOR:** The analytics page should include a search bar that allows managers to search for specific orders while retaining the existing filters for date range, store, and other relevant criteria.

**STEPS TO REPRODUCE:**
1. Navigate to the analytics page.
2. Attempt to search for a specific order using the existing filters.
3. Notice that there is no search bar available to search for specific orders.

**ERROR MESSAGE:** N/A

**SCREENSHOT:** N/A

**NOTES:** 
- Would enhance UX by allowing managers to quickly find specific order data
- Makes analytics page more efficient and user-friendly

---

## Bug 30: Guest Checkout Missing Card Entry UI
**REPORTER:** Braxton
**PAGE URL:** http://0.0.0.0:8000/orders/checkout/

**BUG DESCRIPTION:** Payment mode still in Demo checkout with nowhere to enter card info.

**BUG TYPE:** UI / Functionality

**CURRENT BEHAVIOR:** No card information entry form visible.

**EXPECTED BEHAVIOR:** Card info box should be present even if backend does not do anything with that information. At least make the frontend look like it is working.

**NOTES:** 
- Story 62 – Guest Checkout

---

## Bug 31: AI Refinement Feature Not Helpful or Intuitive
**REPORTER:** Braxton
**PAGE URL:** http://0.0.0.0:8000/orders/menu/A001/midnight-cola-zero/

**BUG DESCRIPTION:** AI Refinement/AI help feature is not super helpful or intuitive with limited variety of input options.

**BUG TYPE:** UX / Feature Design

**CURRENT BEHAVIOR:** Formatting and options make it unclear what the AI is changing; limited input variety.

**EXPECTED BEHAVIOR:** Formatting should be changed to help user understand what the AI is changing and provide options to accept some changes or decline others.

**NOTES:** 
- Story 63 & 65 – Drink Customization
- The button doesn't actually look like a button
- Does use saved preferences which is nice

---

## Bug 32: Favorites Card Sizing Inconsistent with 3 Items
**REPORTER:** Braxton
**PAGE URL:** http://0.0.0.0:8000/orders/favorites/

**BUG DESCRIPTION:** Card sizing is slightly off for the middle card when there are exactly 3 drinks saved in Favorites.

**BUG TYPE:** UI / Layout

**CURRENT BEHAVIOR:** Middle card is different size than other cards when exactly 3 drinks are in favorites. Works fine with other amounts.

**EXPECTED BEHAVIOR:** All card sizes should be equal regardless of number of drinks.

**NOTES:** 
- Story 45 – Favorites
- Could allow adding to favorites by selecting checkbox without adding to order

---

## Bug 33: AI Drink Generation Shows Redundant Ideas
**REPORTER:** Braxton
**PAGE URL:** http://0.0.0.0:8000/orders/menu/A001/

**BUG DESCRIPTION:** AI gives "Drink Ideas" below the generate drink ideas section, which duplicates information already shown in AI pick.

**BUG TYPE:** UX / Redundancy

**CURRENT BEHAVIOR:** "Drink Ideas" shown twice - once in AI pick and once below.

**EXPECTED BEHAVIOR:** Remove redundant "Drink Ideas" section since it's already shown.

**NOTES:** 
- Story 6 – AI Analysis

---

## Bug 34: Chatbot Cannot Fulfill Stated Support Capabilities
**REPORTER:** Braxton
**PAGE URL:** http://0.0.0.0:8000/support/

**BUG DESCRIPTION:** Chat Bot claims it can help with pickup timing or cancelling orders but cannot do either of those.

**BUG TYPE:** Functionality / Missing Implementation

**CURRENT BEHAVIOR:** Bot has lots of problems; doesn't actually fulfill claimed capabilities.

**EXPECTED BEHAVIOR:** Full support for anything to do with FloatStack or remove misleading capability claims.

**NOTES:** 
- Story 6 – AI Analysis
- AI Chat Bot section

---

## Bug 35: Refund Flow Crashes with HTTP 500 When No Revenue Record Exists
**REPORTER:** Peyton
**PAGE URL:** `/backend/chatbot/`

**BUG DESCRIPTION:** The chatbot refund flow throws a server error if the selected order does not already have a matching Revenue row.

**BUG TYPE:** Backend / Error Handling

**CURRENT BEHAVIOR:** After confirming an order for refund, backend crashes with `Revenue matching query does not exist`.

**EXPECTED BEHAVIOR:** The refund flow should either create/fetch the revenue record safely or return a friendly failure message instead of crashing.

**STEPS TO REPRODUCE:**
1. Create an order without creating a corresponding revenue entry.
2. POST to `/backend/chatbot/` with a refund request.
3. Advance the refund flow until the confirmation step.
4. Confirm the refund with `yes`.
5. Observe a server-side HTTP 500 error.

**ERROR MESSAGE:** `backend.models.Revenue.DoesNotExist: Revenue matching query does not exist.`

**SCREENSHOT:** N/A

**NOTES:** 
- Verified live on 2026-04-10
- Blocks Story 50 unless revenue creation is guaranteed before every refund attempt

---

## Bug 36: Failed Stripe Refund Still Marks Revenue as Refunded
**REPORTER:** Peyton
**PAGE URL:** `/backend/chatbot/` and `/backend/revenues/`

**BUG DESCRIPTION:** If Stripe refund processing fails, the revenue record is still marked `Refunded: true`.

**BUG TYPE:** Logic / Data Integrity

**CURRENT BEHAVIOR:** Chatbot returns error message about failed refund, but `/backend/revenues/` shows the order as refunded anyway.

**EXPECTED BEHAVIOR:** Revenue should only be marked refunded after Stripe confirms a successful refund.

**STEPS TO REPRODUCE:**
1. Create an order and a matching revenue record.
2. Start the refund flow through `/backend/chatbot/`.
3. Confirm the refund with `yes`.
4. Use current placeholder Stripe keys so refund attempt fails.
5. Check `/backend/revenues/` for the order.

**ERROR MESSAGE:** Chatbot response: `Sorry, There was a problem processing the refund. Please try again later!`

**SCREENSHOT:** N/A

**NOTES:** 
- Verified live on 2026-04-10
- Refund path updates Revenue row before checking whether `refund_order()` succeeded

---

## Bug 37: Orders Endpoint Allows Anonymous Access
**REPORTER:** Peyton
**PAGE URL:** `/backend/orders/`

**BUG DESCRIPTION:** The general orders endpoint is open without authentication, allowing unauthenticated clients to view and create orders directly.

**BUG TYPE:** Security / Permissions

**CURRENT BEHAVIOR:** Anonymous requests can GET `/backend/orders/` and POST `/backend/orders/` successfully.

**EXPECTED BEHAVIOR:** Order creation and order listing should be restricted by role and authentication. Guest checkout, if allowed, should use a tightly scoped guest-safe flow.

**STEPS TO REPRODUCE:**
1. Make an unauthenticated GET request to `/backend/orders/`.
2. Observe the full orders list is returned.
3. Make an unauthenticated POST request to `/backend/orders/` with UserID, Drinks, and StripeID.
4. Observe that the order is created successfully.

**ERROR MESSAGE:** N/A

**SCREENSHOT:** N/A

**NOTES:** 
- Verified live on 2026-04-10
- Direct Story 27 / cross-role permissions issue

---

## Bug 38: Inventory Endpoints Allow Anonymous Read and Write Access
**REPORTER:** Peyton
**PAGE URL:** `/backend/inventory/report/` and `/backend/inventory/<id>/`

**BUG DESCRIPTION:** Inventory data can be read and mutated without logging in.

**BUG TYPE:** Security / Permissions

**CURRENT BEHAVIOR:** Anonymous callers can access `/backend/inventory/report/` and can PATCH `/backend/inventory/1/` with `{"used_quantity":1}` successfully.

**EXPECTED BEHAVIOR:** Inventory reporting and especially inventory mutation should require manager/admin authorization.

**STEPS TO REPRODUCE:**
1. Make an unauthenticated GET request to `/backend/inventory/report/`.
2. Observe a 200 response with inventory data.
3. Make an unauthenticated PATCH request to `/backend/inventory/1/` with `{"used_quantity":1}`.
4. Observe a 200 response and updated inventory quantity.

**ERROR MESSAGE:** N/A

**SCREENSHOT:** N/A

**NOTES:** 
- Verified live on 2026-04-10
- Direct permissions failure

---

## Bug 39: Test Accounts Unavailable Until Manual Database Population
**REPORTER:** Peyton
**PAGE URL:** `/backend/auth/login/`

**BUG DESCRIPTION:** The repo starts with a migrated but empty database, so documented seeded users (`super`, `staff`, `test`, `test2`) cannot log in until someone manually runs the population command.

**BUG TYPE:** Setup / Test Environment

**CURRENT BEHAVIOR:** Login fails with "Unable to log in with provided credentials" immediately after startup if `populate_db` has not been run.

**EXPECTED BEHAVIOR:** README should clearly require seeding before testing, or the standard startup flow should automatically provide the documented starter accounts.

**STEPS TO REPRODUCE:**
1. Start with a migrated database that has no user rows.
2. Attempt to log in as `super` / `staff` / `test` using the README credentials.
3. Observe login failure.
4. Run `python manage.py populate_db`.
5. Retry login and observe that the accounts now work.

**ERROR MESSAGE:** `{"non_field_errors":["Unable to log in with provided credentials."]}`

**SCREENSHOT:** N/A

**NOTES:** 
- Verified live on 2026-04-10
- Primarily a testing blocker
- Will slow everyone on testing sprint if setup instructions stay ambiguous

---

## Bug 40: Repairs Feature Not Implemented
**REPORTER:** Peyton
**PAGE URL:** N/A

**BUG DESCRIPTION:** Repairs stories appear to have no implementation surface in the current repo.

**BUG TYPE:** Missing Functionality / Scope Gap

**CURRENT BEHAVIOR:** No repair models, API routes, screens, scheduling UI, CSV import flow, or priority workflow found in codebase.

**EXPECTED BEHAVIOR:** Stories 9, 10, 11, and 12 should have identifiable models/endpoints/screens/flows available for testing.

**STEPS TO REPRODUCE:**
1. Search the repo for `repair`, `schedule`, `priority`, and repair-related CSV handlers.
2. Observe that there are no dedicated repair feature files or routes in app code.
3. Attempt to identify a repair workflow in the UI or backend API surface.
4. Observe no clear repair feature path to test.

**ERROR MESSAGE:** N/A

**SCREENSHOT:** N/A

**NOTES:** 
- Test blocker for Stories 9 & 11, Story 10, and Story 12
- If implementation exists in another branch, environment will be needed before testing

---

## Bug 41: Super Admin Login Returns Both Admin and Manager Flags
**REPORTER:** Peyton
**PAGE URL:** `/backend/auth/login/`

**BUG DESCRIPTION:** Logging in as a super admin returns both `is_admin: true` and `is_manager: true`, which blurs role boundaries.

**BUG TYPE:** Permissions / Role Modeling

**CURRENT BEHAVIOR:** Super admin responses indicate the account is both admin and manager because Django `is_superuser` and `is_staff` are both true.

**EXPECTED BEHAVIOR:** Cross-role checks should expose one clear effective role, or the frontend/backend should explicitly support multi-role behavior without ambiguity.

**STEPS TO REPRODUCE:**
1. Log in as the `super` account.
2. Inspect the response JSON from `/backend/auth/login/`.
3. Observe both `is_admin` and `is_manager` are true.

**ERROR MESSAGE:** N/A

**SCREENSHOT:** N/A

**NOTES:** 
- Frontend currently routes to admin first, so doesn't always break navigation
- Risky for cross-role permission tests because API contract is ambiguous

---

## ARCHITECTURAL RECOMMENDATION: Switch Distribution Model from Per-Store to Per-Region

**ISSUE:** Current distributed architecture is per-store (one instance per store). This doesn't scale and doesn't match real-world organization.

**CURRENT MODEL:**
- Instance 8001 = Store A001 only (Chicago)
- Instance 8002 = Store B001 only (Jersey)
- Instance 8003 = Store C001 only (Logan)
- Problem: 50+ stores = 50+ instances (unmanageable)

**RECOMMENDED MODEL:**
- Instance 8001 = Region A (Chicago hub) → contains stores A001, A002, A003, etc.
- Instance 8002 = Region B (Jersey hub) → contains stores B001, B002, B003, etc.
- Instance 8003 = Region C (Logan hub) → contains stores C001-C008, etc.

**WHY:**
1. **Real-world alignment**: Regions have supply hubs; stores belong to regions, not vice versa
2. **Logistics scope**: Logistics managers manage regions, not individual stores
3. **Scalability**: Hundreds of stores fit into ~5-10 regional instances
4. **Data locality**: Related stores (same region) co-located in same DB for transfers/sync
5. **Repair scope**: Repair teams service regions, already scoped by region

**IMPACT:**
- Fixes Bug 2 (stores from other nodes) partially—users see all stores in their region
- Requires refactoring `docker-compose.multi.yml` to use regions instead of stores
- Requires updating `STORE_ID_MAPPING` to map regions instead of stores
- Requires updating bootstrap seed to include all region stores in one instance

**EFFORT:** Medium (refactor docker-compose, seed, environment mappings)

**DECISION:** TBD - Architectural decision required from team
