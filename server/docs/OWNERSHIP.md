# Canonical Ownership Map

This document defines which Django app owns which models, services, and responsibilities. All new feature work must follow these boundaries. If you're unsure where something belongs, check this document first.

---

## App Ownership

### `users`
**Owns:** authentication, authorization, user profiles, scoping

| Model | Purpose |
|-------|---------|
| `User` | Custom user model with role enum (account_user, manager, admin, logistics_manager, repair_staff, super_admin) |
| `UserStoreAssignment` | Links a user to a store with an assignment type |
| `UserRegionAssignment` | Links a user to a region with an assignment type |
| `TastePreference` | Account user ingredient preferences for AI recommendations |
| `FavoriteDrink` | Account user saved drink configurations |

**Source of truth for:** who a user is, what role they have, which stores/regions they can access.

**Key services:** permission helpers (`permissions.py`), role-aware navigation (`selectors.py`), login/registration (`views.py`)

---

### `stores`
**Owns:** geographic structure — regions and store locations

| Model | Purpose |
|-------|---------|
| `Region` | One of 7 geographic regions (A–G) |
| `Store` | A physical store location belonging to a region |

**Source of truth for:** where stores are, which region they belong to, store metadata (address, coordinates, timezone).

**Key services:** store/region lookup helpers (`selectors.py`), geolocation utilities (`location.py`)

---

### `orders`
**Owns:** customer ordering lifecycle from cart to pickup

| Model | Purpose |
|-------|---------|
| `Order` | A customer order scoped to exactly one store |
| `OrderItem` | A line item within an order (snapshot of drink at time of order) |
| `GuestOrderContact` | Contact info for guest (non-account) orders |

**Source of truth for:** order state, order pricing, fulfillment status. Every order belongs to exactly one store.

**Key services:** order creation, state transitions (`services.py`), drink catalog (`catalog.py`), staff order queue (`selectors.py`)

---

### `payments`
**Owns:** payment processing, revenue tracking

| Model | Purpose |
|-------|---------|
| `PaymentTransaction` | One-to-one with Order — Stripe or mock payment record |
| `RevenueLedgerEntry` | Durable financial record (sale, refund, adjustment) per store |

**Source of truth for:** payment status, revenue figures. The server recalculates pricing — client-submitted totals are never trusted.

**Key services:** payment lifecycle (`services.py`), Stripe/mock boundary

---

### `inventory`
**Owns:** item catalog, store-level stock, local suppliers, usage tracking, alerts

| Model | Purpose |
|-------|---------|
| `InventoryItem` | Global catalog definition (SKU, category, thresholds) |
| `StoreInventoryBalance` | On-hand and reserved quantities per store per item |
| `LocalSupplier` | Third-party supplier within a region |
| `SupplierReplenishment` | Record of a supplier delivery to a store |
| `RestockAlert` | Low-stock warning scoped to a store + item |
| `SupplyUsageRecord` | Historical usage data (often from CSV import) |
| `SupplySchedule` | AI-generated or human-approved recurring restock plan |

**Source of truth for:** what items exist, how much stock each store has, when to reorder.

**Key services:** inventory deduction at order queue, restock evaluation, transfer recommendations (`services.py`, `selectors.py`)

---

### `supply_hubs`
**Owns:** regional hub inventory, inter-store/hub supply transfers

| Model | Purpose |
|-------|---------|
| `SupplyHub` | A regional supply hub (one per region) |
| `HubInventoryBalance` | On-hand and reserved quantities per hub per item |
| `SupplyTransfer` | A supply movement between stores/hubs with full state machine |
| `SupplyTransferLineItem` | Individual items within a transfer |

**Source of truth for:** hub stock levels, transfer status and approvals. Transfer scope rules: same-region store-to-store, hub-to-store, or cross-region hub within 1000 miles.

---

### `maintenance`
**Owns:** machine registry, status tracking, repair scheduling

| Model | Purpose |
|-------|---------|
| `MachineType` | Type definition with service intervals and warning thresholds |
| `Machine` | A physical machine at a store |
| `MachineStatusEvent` | Status change history for a machine |
| `RepairAssignment` | A scheduled repair task assigned to repair_staff |
| `MaintenancePolicy` | Configurable service rules per machine type and region |

**Source of truth for:** machine health, service schedules, repair assignments.

---

### `imports`
**Owns:** CSV upload, validation, and processing

| Model | Purpose |
|-------|---------|
| `ImportJob` | Tracks a CSV import (supply_usage or repair_status) with row counts and error reports |

**Source of truth for:** import history and validation results. Imported data flows into `inventory` (usage records) or `maintenance` (status events).

---

### `notifications`
**Owns:** in-app notification delivery

| Model | Purpose |
|-------|---------|
| `Notification` | A notification message for a specific user |

---

### `sync`
**Owns:** outbox events for simulated inter-node communication, audit logging

| Model | Purpose |
|-------|---------|
| `SyncOutboxEvent` | Durable record of a change that should be synced to other nodes |
| `AuditLog` | Record of staff actions for accountability |

**Source of truth for:** what changes have been dispatched and their delivery status.

---

### `analytics`
**Owns:** reporting, dashboard aggregation, AI recommendation inputs

| Models | None currently — reads from other apps |
|--------|----------------------------------------|

**Key services:** dashboard payload builder (`selectors.py`), drink recommendations (`recommendations.py`)

---

## Cross-App Rules

1. **Business logic goes in services, not model `save()` methods** — unless the rule is truly local to one model.
2. **Apps should not import each other's models directly in models.py** — use string FK references (`"stores.Store"`).
3. **Permission checks happen in `users.permissions`** — other apps call those helpers, they don't roll their own.
4. **Inventory deduction happens at order queue commitment** — not in the browser, not at pickup.
5. **AI outputs are recommendations only** — a human (logistics_manager) must approve before they become operational.

## Deprecated / Not Used

- There is no `DrinkTemplate` database model. The drink catalog is defined in `orders/catalog.py` as a Python data structure. If a DB-backed catalog is needed later, it belongs in `orders`.
- `general_user` is not a role in the `User.Role` enum. Guest users are handled via `GuestOrderContact` on the order, not as User records.

## Where New Features Go

| If you're building... | It belongs in... |
|----------------------|-----------------|
| New drink customization options | `orders` (catalog.py) |
| Store-level operational feature | The relevant domain app, scoped to a store FK |
| Region-level coordination | `supply_hubs` or `maintenance` depending on domain |
| A new dashboard panel | The relevant app's `selectors.py` + a template partial |
| A new CSV import type | `imports` (new ImportType + processing logic) |
| A new notification trigger | `notifications` (called from the originating app's service) |
| A new background job | A `tasks.py` in the relevant app, registered via Celery autodiscovery |
