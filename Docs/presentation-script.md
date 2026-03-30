# CodePop Presentation Script

## Opening

"CodePop is a Django + HTMX operations platform that combines customer ordering with store, logistics, repair, analytics, and sync workflows in one scoped product."

## Demo Beats

1. Show the home page and explain the web-first architecture plus role-scoped dashboards.
2. Log in as manager and show the order queue, revenue summary, low-stock alerts, and scoped notifications.
3. Log in as admin and show store-scoped user management plus audit activity.
4. Log in as repair staff and show the urgency-first maintenance queue, route grouping, and one live assignment action.
5. Log in as logistics and show transfers, supply imports, AI draft schedules, and sync projections/conflicts.
6. In sync, resolve or ignore one conflict to show reconciliation controls.
7. Log in as super admin and show cross-region analytics, daily revenue, order-backed financial rows, maintenance summaries, sync health, and oversight panels.
8. End with a guest or account order flow to show the customer side is still integrated into the same system.

## Key Phrases

- "The server stays the source of truth for permissions, pricing, and operational workflows."
- "Outbox events are durable, observable, and replayable."
- "Conflicts are intentionally simple: stale events are ignored and logged instead of silently overwriting state."
- "Maintenance and notifications are event-driven rather than view-driven shortcuts."

## Closing

"The canonical path is the Django application under `server/`. The old mobile-first direction is retired from the active workspace, and this repo is now organized around the rewritten CodePop architecture."
