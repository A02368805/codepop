# Legacy Cutover Notes

## Canonical Active Path

- Django modular-monolith apps in `server/apps/`
- Server-rendered templates and HTMX partials in `server/templates/`
- Root URL routing in `server/config/urls.py`

## Retired From Active Scope

- Old standalone starter templates (`server/templates/base.html`, `server/templates/login.html`, `server/templates/drink_builder.html`, `server/templates/drink_list.html`)
- Old starter styling path tied to those templates (`server/static/css/style.css`)

These retired files were not part of the canonical URL map and are removed to avoid architecture drift.

## Group 3 Cutover Check

- No active dashboard uses legacy template inheritance.
- Maintenance, sync, analytics, imports, and notifications all route through canonical app modules.
- Sync visibility and conflict handling remain centralized in `/sync/` with auditable actions.
