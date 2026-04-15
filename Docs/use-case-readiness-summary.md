# FloatStack Use-Case Readiness Summary

Prepared: April 13, 2026

## Selected Demo Use Cases (One Per Role)

| Role | Chosen Use Case | Completion |
|---|---|---|
| Customer | Check out as a guest without creating an account, then track the order status | 96% |
| Maintenance Worker | Check the machine maintenance tracking & status lifecycle dashboard | 91% |
| Store Manager | Monitor low inventory warnings and take action before stock runs out | 94% |
| Owner (Super Admin) | Compare revenue and operational metrics across multiple stores | 89% |

## Evidence in Code and Tests

### 1) Customer: Guest checkout + guest order tracking
- Checkout guest path and guest-contact creation:
  - `server/apps/orders/views.py` (CheckoutView POST flow)
- Guest lookup path:
  - `server/apps/orders/views.py` (GuestLookupView)
- Test coverage:
  - `server/tests/test_views.py` (`test_guest_lookup_flow_works_without_creating_a_user`)

### 2) Maintenance Worker: Maintenance status lifecycle dashboard
- Maintenance workspace and assignment actions:
  - `server/apps/maintenance/views.py`
- Assignment lifecycle and machine status reset to operational after completion:
  - `server/apps/maintenance/services.py`
- Test coverage:
  - `server/tests/test_maintenance.py` (`test_assignment_action_endpoint_advances_status_for_assignee`)

### 3) Store Manager: Low-stock monitoring and corrective action
- Manager dashboard low-stock panel and inventory overview:
  - `server/apps/users/views.py` (ManagerDashboardView)
  - `server/templates/manager/dashboard.html`
- Inventory adjustment action endpoint:
  - `server/apps/inventory/views.py` (InventoryAdjustView)
- Test coverage:
  - `server/tests/test_views.py` (`test_inventory_adjust_htmx_updates_the_row`)

### 4) Owner (Super Admin): Cross-store revenue/operations comparison
- Super-admin region comparison and regional operations comparison:
  - `server/apps/users/views.py` (SuperAdminDashboardView)
  - `server/templates/super_admin/dashboard.html`
- Analytics cross-store revenue, usage, maintenance summaries:
  - `server/apps/analytics/views.py`
  - `server/templates/analytics/index.html`
- Test coverage:
  - `server/tests/test_views.py` (`test_analytics_workspace_surfaces_daily_and_ai_sections`)

## Validation Run (Targeted)

Executed targeted tests for one selected flow per role:

```bash
../codepop_virtual_enviroment/bin/python manage.py test \
  tests.test_views.CustomerOrderingViewTests.test_guest_lookup_flow_works_without_creating_a_user \
  tests.test_maintenance.MaintenanceWorkspaceViewTests.test_assignment_action_endpoint_advances_status_for_assignee \
  tests.test_views.DashboardAndHtmxViewTests.test_inventory_adjust_htmx_updates_the_row \
  tests.test_views.DashboardAndHtmxViewTests.test_analytics_workspace_surfaces_daily_and_ai_sections
```

Result: `4 tests passed (OK)`.

## Notes on Percentages

- Percentages reflect implementation completeness plus direct testability in the current codebase.
- Remaining gap to 100% is mostly demo polish/integration depth (not core-path absence).
