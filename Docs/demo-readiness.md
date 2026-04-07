# FloatStack Demo Readiness Notes

## Payments

- `PAYMENT_MODE=mock` is the default demo path and keeps checkout fully local.
- `PAYMENT_MODE=stripe` enables the Stripe checkout boundary, success/cancel handlers, and webhook endpoint.
- Pricing remains server-authoritative in both modes.

## Background Work

- Imports queue through Celery tasks.
- Outbox sync processing runs through worker tasks plus a beat schedule for retries.
- Notification creation is immediate in-app, with a background dispatch hook for external channels.
- Recommendation refreshes run after preference changes and queued account orders.

## Geolocation

- The store recommendation page can request browser coordinates and submit them back to the server.
- Manual coordinates and preferred-store selection remain valid fallbacks.
- Distance scoring stays server-side so map-provider tokens can be layered in later without changing the view contract.

## Notifications

- In-app notifications are fully supported.
- `FCM_SERVER_KEY`, `WEB_PUSH_PUBLIC_KEY`, and `WEB_PUSH_PRIVATE_KEY` are exposed as future integration hooks.
- No browser subscription/device-management UI is stored yet.

## Demo Workflows Backed By Seed Data

- Guest order and lookup using `FS-M5K9TD`, pickup combo `624`, and backup code `GST-DEMO-001`
- Account ordering and recommendations through `account.casey@floatstack.local`
- Manager inventory and revenue through `manager.c001@floatstack.local`
- Logistics transfers/imports/sync through `logistics.c@floatstack.local`
- Repair queue and maintenance imports through `repair.north@floatstack.local`
- System-wide oversight through `superadmin@floatstack.local`

## Honest Gaps

- External downstream sync connectors are still placeholders behind the outbox.
- Push delivery is hook-ready but not a full production notification system.
- Demo analytics are intentionally useful and explainable, but not deeply configurable yet.
