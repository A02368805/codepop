# FloatStack Test Design Report

## How We Test

We write automated tests to catch logic bugs (orders, payments, permissions) and manually test to catch things automated tests miss (layout, formatting, weird edge cases).

---

## What We're Worried About

**Mobile layout.** Tests verify we send the right HTML, but don't catch if buttons are misaligned or form inputs are broken on small screens.

**CSV parsing.** We test clean UTF-8 files. Weird encodings, Windows line breaks, or embedded quotes might break the parser.

**Multi-store sync.** We fake network calls in tests. Real delays and out-of-order changes might cause issues.

**Concurrent edits.** If two managers edit the same inventory item at the exact same time, one might lose their change.

**Background tasks.** Tests run them instantly; production runs them separately. We don't know if that causes timing bugs.

---

## Code Coverage

**Overall: 78%** of code is tested by automated tests.

Models are rock solid (95%+): inventory, orders, payments, stores, sync, supply hubs. These are the critical data structures and we're confident they work right.

Services and selectors are well-tested (85-90%): order services, sync services, user selectors. The business logic is solid.

Views are weaker (39-92% depending on the app). Store views and forms are undercooked (33-44% on stores forms and location). Order views hit 60%, payment views 62%. This is where most manual testing bugs will be.

The AI assistant code (orders/assistant.py) is only 21% tested—it's specialized and hard to test, so it'll need manual vetting.

Run `make coverage` anytime to see the full breakdown.

---

## Manual Testing Plan

Instead of generic test scenarios, we're testing the actual user stories from our requirements document. Each story represents a real user workflow, and we'll verify each one works end-to-end.

### Guest/General User Stories

**Story 62**: As a general_user, I want to place orders without creating an account so that I can try the service without a registration barrier.
- Steps: Navigate to home, find a store, customize a drink, check out with test card, verify order is created.
- Verify: Can place order without login. Payment completes. Order code is unique and findable.

**Story 59**: As a general_user, I want to select a store location manually so that I can order from a specific location without enabling geolocation.
- Steps: Go to stores, manually enter a location or click a store from the list (without geolocation permission), customize, checkout.
- Verify: Store selection works without geolocation. Form accepts manual location. Checkout completes.

**Story 63 & 65**: As a general_user, I want to customize drinks using available ingredients and see all available options.
- Steps: Browse menu, verify all syrups/sodas/ice cream show up, click each option to customize, add to cart.
- Verify: All ingredients display correctly. Customization options work. Cart reflects selections.

**Story 67**: As a general_user, I want a full refund if I cancel my order before preparation begins.
- Steps: Place order, immediately go back, cancel before it moves to "preparing," verify refund message shows.
- Verify: Refund is processed immediately. Order status updates to canceled.

---

### Account User Stories

**Story 40**: As an account_user, I want to sign in using secure authentication.
- Steps: Log in with valid credentials, verify dashboard appears, log out, try to access protected page (should redirect).
- Verify: Login works. Sessions persist. Logout clears session. Protected pages redirect.

**Story 45**: As an account_user, I want to save drinks to a favorites list so that I can reorder them with a single tap.
- Steps: Log in, find a drink, click "save favorite," go to favorites list, click a favorite to re-order.
- Verify: Favorite saves. Appears in favorites list. Can re-order from favorite.

**Story 42**: As an account_user, I want drinks recommended based on my order history and stated preferences.
- Steps: Set taste preference (sweet/sour/fruity), check recommendations page, verify drinks appear.
- Verify: Preferences save. Recommendations display. Recommendations change when preferences change.

**Story 46 & 47**: As an account_user, I want my drink prepared close to my arrival time OR specify a pickup time manually.
- Steps: Log in, order a drink, select "ASAP" (geolocation) and then try "scheduled time" option.
- Verify: Both pickup options show up. Can select either. Order confirms with correct pickup time.

**Story 50**: As an account_user, I want a full refund processed within 24 hours if I cancel my order before preparation.
- Steps: Log in, place order, go to order history, click order, click "cancel," verify refund confirmation.
- Verify: Refund button only shows before "preparing" status. Refund is processed. Status changes to "refunded."

---

### Manager Stories

**Story 32**: As a manager, I want to view inventory levels for my store.
- Steps: Log in as manager, go to inventory page, verify items show with current quantities.
- Verify: Inventory page loads. Items display. Can see quantities for syrups, sodas, ice cream.

**Story 33**: As a manager, I want to receive notifications when inventory drops below defined thresholds so that I can reorder.
- Steps: Set an item's threshold to 10, reduce quantity below 10, verify alert shows on dashboard.
- Verify: Restock alerts appear when threshold is crossed. Alerts show which item needs reorder.

**Story 34**: As a manager, I want access to revenue and payment reports.
- Steps: Log in as manager, go to dashboard or reports page, verify revenue metrics display (daily total, avg order value, etc).
- Verify: Revenue numbers display. Reports show today's sales. Numbers are correct (match order count and payment amounts).

(Add specific order queue testing) As a manager, I want to view orders queued for preparation and move them through statuses.
- Steps: Log in as manager, go to order queue, click an order, move it to "preparing," verify status updates immediately without page reload.
- Verify: Queue displays orders. Status changes persist. HTMX inline edits work.

---

### Logistics Manager Stories

**Story 2**: As a logistics_manager, I want to view supply levels for all stores I manage.
- Steps: Log in as logistics person, go to supply dashboard, verify stores in my region show with quantities.
- Verify: Only my region's stores appear. Quantities display. Can see which stores need restocking.

**Story 5**: As a logistics_manager, I want to import supply usage data from structured files.
- Steps: Go to imports, upload a CSV with supply data, wait a few seconds, verify import completes and shows row count.
- Verify: CSV upload works. File processes. Row count displays. Inventory updates from import.

**Story 6**: As a logistics_manager, I want AI to analyze supply usage patterns.
- Steps: After importing data, go to analytics or trends page, verify system shows usage patterns or forecasts.
- Verify: Analytics display after import. Patterns or forecasts appear (even if just demo data).

---

### Repair Staff Stories

**Story 9 & 11**: As repair_staff, I want to manage repair schedules and track machine status.
- Steps: Log in as repair staff, go to maintenance page, verify machines show with status (warning, error, ok).
- Verify: Machine list displays. Status is clear. Can see which machines need attention.

**Story 10**: As repair_staff, I want to import machine repair data from structured files.
- Steps: Go to imports, upload a maintenance CSV, wait, verify machines are added/updated.
- Verify: CSV upload works. Machine count increases. New machines appear in list.

**Story 12**: As repair_staff, I want to see machines that are out-of-order or in error status so I can prioritize urgent repairs.
- Steps: After import, filter or sort machines by status, verify out-of-order machines appear at top.
- Verify: Urgent machines are visible. Can identify which need immediate attention.

---

### RBAC and Admin Stories

**Story 17**: As a super_admin, I want to access data for any store location.
- Steps: Log in as super admin, access a specific store's data (inventory, orders, revenue).
- Verify: Can view all stores. Can see all their data. No 403 errors.

**Story 22 & 23**: As an admin, I want to manage user accounts for my store only. I want to unlock, disable, or remove accounts.
- Steps: Log in as admin, go to user management, disable a user account, verify user can't log in after.
- Verify: Can manage users. Can disable accounts. Disabled users are blocked from login.

**Story 27**: As an admin, I want to add or remove manager permissions.
- Steps: Go to user management, find a user with manager role, remove the manager permission, verify they lose access to `/manager/`.
- Verify: Permission changes take effect. Users lose access when permission is removed.

---

### Cross-Role Permission Tests

Test that unauthorized roles cannot access restricted pages:
- Customer trying to access `/manager/` → 403 or redirect
- Manager trying to access `/logistics/` → 403 or redirect
- Repair staff trying to access `/orders/` → 403 or redirect
- Logistics person trying to access another region's stores → not in filters

Verify data filtering works:
- Each manager only sees their store
- Each logistics person only sees their region
- Each customer only sees their own orders and favorites

---

## What Will Probably Break

Mobile layout issues. HTMX updates not showing up. CSV files with weird encodings. Missing permission checks on a few pages. Sync not waking up to send changes.

---

## Summary

We're testing against 20+ actual user stories from our requirements document. Each story is a real workflow that a user expects to work. If a story passes, the system works for that use case. If it fails, we document it and fix it. After testing, we'll note which stories passed, which failed, and what we had to fix.
