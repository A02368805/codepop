# FloatStack Migration Plan

## Source Of Truth

The migration follows the rewritten documents, not the old starter assumptions:

- `Docs/CodePop_High_Level_Design_Rewritten.md`
- `Docs/CodePop_Low_Level_Design_Rewritten.md`
- `Docs/RequirementsDoc_Rewritten.md`

## What Was Kept

- The repository and design-document set
- Django as the backend foundation
- useful legacy CSV data copied into `codepop_backend/seed/csv/legacy_catalog/`

## What Was Deleted From The Active Architecture

- Expo/React-Native as the primary frontend
- the old single-file Django settings layout
- token-first/mobile-first starter assumptions
- unused placeholder dashboard base templates from the early scaffold

Archived starter code lives under `legacy/` instead of remaining active.

## What Was Moved

- `codepop/` -> `legacy/expo_starter/codepop/`
- root `package.json` and `package-lock.json` -> `legacy/expo_starter/`
- `codepop_backend/backend/` -> `legacy/django_starter_backend/backend/`
- `codepop_backend/codepop_backend/` -> `legacy/django_starter_backend/codepop_backend/`
- old cleanup scripts -> `legacy/django_starter_backend/`

## Active Architecture Decisions

- Django + HTMX is the primary UI architecture
- session authentication is the default auth mechanism
- the backend is organized as a modular monolith under `codepop_backend/apps/`
- PostgreSQL is the primary database target, with SQLite fallback for fast local development
- Celery + Redis power imports, outbox sync processing, retry scheduling, and recommendation hooks
- role-aware navigation is generated on the server and backed by server-side RBAC and scoping checks
- payments are server-authoritative and routed through a clean `mock` or Stripe-ready gateway boundary
- the sync outbox and audit log are first-class internal operational surfaces, not hidden internals

## Prompt 4 Completion Notes

- Added background tasks for queued CSV imports, notification dispatch hooks, sync processing, and recommendation refreshes
- Added geolocation-assisted store recommendation with browser fallback to manual selection
- Added payment-mode-aware checkout and a Stripe webhook/cancel/success boundary
- Added analytics summaries for revenue, supply usage, machine failures, and store/region comparisons
- Added stronger validation, 500 handling, explicit auth guards on sensitive HTMX endpoints, and final demo docs

## Starter Reuse Rationale

- The old Expo frontend did not fit the rewritten multi-dashboard web-first product, so it was archived.
- The old backend internals were too tightly coupled to the starter’s token/API assumptions, so a clean modular monolith was safer.
- Legacy CSVs were still useful for seed references and import examples, so they were preserved in the new seed area.

## Remaining Follow-On Cleanup

- Swap from demo/mock configuration to live Stripe and external notification credentials when a real deployment is ready
- Add true downstream sync connectors if the outbox needs to publish beyond the local monolith
- Expand push-notification subscriptions, production monitoring, and accessibility polish as a post-demo hardening pass
