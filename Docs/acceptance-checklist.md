# Group 3 Acceptance Checklist

## Operational Workflows

- Maintenance workspace shows urgent machines, route batches, assignment cards, and audit-backed status history.
- Repair staff can acknowledge, start, block, update, complete, and close assignments through the canonical maintenance views.
- In-app notifications are visible, unread/read aware, and scoped by role, store, and region.
- Sync workspace shows outbox health, receiver projections, and conflict logs.
- Analytics workspace shows scoped revenue, daily summaries, maintenance summaries, AI draft schedules, and audit visibility.

## Role Dashboards

- Manager dashboard uses real scoped store data.
- Admin dashboard uses real scoped user and audit data.
- Logistics dashboard uses real scoped transfer, import, and hub data.
- Repair dashboard is urgency-first and actionable.
- Super admin dashboard shows cross-region operational summaries.

## Security And QA

- Session and CSRF defaults remain enabled in Django settings.
- Stripe webhook requests reject invalid signatures.
- Scope tests cover store and region isolation.
- Sync tests cover projection creation, stale-event handling, and conflict logging.
- Demo-critical dashboard and workflow tests pass.

## Demo And Delivery

- `python manage.py bootstrap_demo_data --reset` seeds a complete local demo.
- `README.md`, `STATUS.md`, `Docs/demo-readiness.md`, and `Docs/demo-runbook.md` all point to the canonical Django path.
- Legacy architecture is clearly documented as retired from the active workspace.
- Full test suite passes locally.
