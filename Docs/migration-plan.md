# CodePop Migration Plan

## Source Of Truth

The migration follows the rewritten documents, not the old starter assumptions:

- `Docs/CodePop_High_Level_Design_Rewritten.md`
- `Docs/CodePop_Low_Level_Design_Rewritten.md`
- `Docs/RequirementsDoc_Rewritten.md`

## What Was Kept

- The repository and design-document set
- Django as the backend foundation
- useful legacy CSV data copied into `server/seed/csv/legacy_catalog/`

## What Was Deleted From The Active Architecture

- Expo/React-Native as the primary frontend
- the old single-file Django settings layout
- token-first/mobile-first starter assumptions
- unused placeholder dashboard base templates from the early scaffold

The archived starter application code is not present in this workspace. What remains are the rewritten docs, older design documents, and copied legacy CSV assets under `server/seed/csv/legacy_catalog/`.

## What Was Moved

- The historical starter code was removed from the active repo tree during the Django cutover.
- The useful parts that were intentionally preserved are the legacy catalog CSVs now stored in `server/seed/csv/legacy_catalog/`.
- Old design documents remain in `Docs/OLD*.md` for reference only and are not the source of truth.

## Active Architecture Decisions

- Django + HTMX is the primary UI architecture
- session authentication is the default auth mechanism
- the backend is organized as a modular monolith under `server/apps/`
- PostgreSQL is the primary database target, with SQLite fallback for fast local development
- Celery + Redis power imports, outbox sync processing, retry scheduling, and recommendation hooks
- role-aware navigation is generated on the server and backed by server-side RBAC and scoping checks
- payments are server-authoritative and routed through a clean `mock` or Stripe-ready gateway boundary
- the sync outbox and audit log are first-class internal operational surfaces, not hidden internals

## Canonical Django Completion Notes

- Added background tasks for queued CSV imports, notification dispatch hooks, sync processing, and recommendation refreshes
- Added geolocation-assisted store recommendation with browser fallback to manual selection
- Added payment-mode-aware checkout and a Stripe webhook/cancel/success boundary
- Added analytics summaries for revenue, supply usage, machine failures, and store/region comparisons
- Added stronger validation, 500 handling, explicit auth guards on sensitive HTMX endpoints, and final demo docs

## Starter Reuse Rationale

- The old Expo frontend did not fit the rewritten multi-dashboard web-first product, so it was retired from the active repo.
- The old backend internals were too tightly coupled to the starter’s token/API assumptions, so a clean modular monolith was safer.
- Legacy CSVs were still useful for seed references and import examples, so they were preserved in the new seed area.

## Remaining Follow-On Cleanup

- Swap from demo/mock configuration to live Stripe and external notification credentials when a real deployment is ready
- Add true downstream sync connectors if the outbox needs to publish beyond the local monolith
- Expand push-notification subscriptions, production monitoring, and accessibility polish as a post-demo hardening pass

## Final Cutover Notes

- The active shared layout is `server/templates/base/base.html`.
- Unreferenced starter-era Tailwind templates such as the old root `base.html`, `login.html`, `drink_builder.html`, and `drink_list.html` were removed from the active template tree.
- The active dashboard, ordering, maintenance, analytics, and sync surfaces all route through the canonical Django apps under `server/apps/`.
