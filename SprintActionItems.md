# Sprint Action Items by Person

> Ready to copy into Monday.com. Each item is a discrete, mergeable unit of work.
> **Priority** = suggested order (do 1 before 2, etc.)
> **Blocked by** = must be merged before this item can start

---

## Gabe — Infrastructure & Notifications

| Priority | Action Item | MUST | Blocked By | Definition of Done |
|---|---|---|---|---|
| 1 | Create 6 Django app skeletons (`accounts`, `orders`, `inventory`, `maintenance`, `notifications`, `core`) using `startapp` | M1 | — | 6 new app folders exist with default files |
| 2 | Add all 6 apps to `INSTALLED_APPS` in `settings.py` | M1 | Gabe #1 | Apps are registered, `makemigrations` runs clean |
| 3 | Set up root `urls.py` with `include()` for each app | M6 | Gabe #1 | Each app's URL namespace is wired: `/api/auth/`, `/api/orders/`, `/api/inventory/`, `/api/maintenance/`, `/api/notifications/`, `/api/core/` |
| 4 | Configure Celery + Redis in `settings.py` and create `celery.py` | M3, M5 | Gabe #2 | `celery_app.config_from_object` works, worker can start |
| 5 | Create `Notification` model in `notifications/models.py` | M6 | Gabe #1 | Model matches LLD §8.2.3: `NotificationID`, `UserID`, `Message`, `Timestamp`, `Type`, `Global` |
| 6 | Build notification CRUD views + URLs in `notifications/` | M6 | Gabe #5 | `GET/POST /api/notifications/`, `GET/PUT/DELETE /api/notifications/<id>/`, user filter, time filter all work |
| 7 | Build super_admin dashboard page | M6 | Peyton #2, Curt #3 | Super admin can see cross-store data: revenue summary, inventory overview, machine status summary, user counts |
| 8 | Build admin dashboard page | M6 | Peyton #2, Curt #3 | Admin can see single-store data: user accounts, inventory, revenue, complaints |

---

## Curt — Core Models, Seed Data & Sync

| Priority | Action Item | MUST | Blocked By | Definition of Done |
|---|---|---|---|---|
| 1 | Create `Store` model in `core/models.py` | M1 | Gabe #1 | Fields: `store_id`, `name`, `address`, `latitude`, `longitude`, `region`, `is_active` |
| 2 | Create `Region` and `SupplyHub` models in `core/models.py` | M1 | Curt #1 | Region has name + hub FK; SupplyHub has location, region; 7 regions defined |
| 3 | Run `makemigrations` and `migrate` for core app | M1 | Curt #2 | All core tables exist in DB, no migration errors |
| 4 | Write `populate_stores` management command | M1 | Curt #3 | Seeds: 7 supply hubs (regions A–G), 20 stores in Region C, 5+ stores per neighboring region |
| 5 | Write `populate_users` management command | M1 | Curt #4, Peyton #2 | Seeds: 1 super_admin, 1 admin per store, 1 manager per store, logistics_manager per region, repair_staff for Region C, 10+ account_users |
| 6 | Write `populate_machines` management command | M1 | Curt #4, Brock #1 | Seeds: 3–5 machines per store with varied statuses and operational dates |
| 7 | Write `populate_inventory` management command | M1 | Curt #4, Braxton #1 | Seeds: 20–30 inventory items per store (sodas, syrups, add-ins, physical); some below threshold |
| 8 | Create sample CSV test files for supply usage and repair schedules | M5 | Curt #4 | 2 CSV files matching LLD §8.4.2 and §8.5.2 formats, 50+ rows each, valid + intentionally invalid rows for testing |
| 9 | Create `ConflictLog` model in `core/models.py` | M1 | Curt #3 | Fields per LLD §7.3.8: `entity_type`, `entity_id`, `conflict_type`, timestamps, resolution |

---

## Peyton — Authentication & RBAC

| Priority | Action Item | MUST | Blocked By | Definition of Done |
|---|---|---|---|---|
| 1 | Define role choices and add `role` field to user model (or UserProfile) in `accounts/models.py` | M2 | Gabe #1 | 7 roles: `super_admin`, `admin`, `manager`, `logistics_manager`, `repair_staff`, `account_user`, `general_user`; each user has exactly one role |
| 2 | Create `store` FK on user profile (nullable for super_admin/general) | M2 | Peyton #1, Curt #1 | Users are tied to a store (or null for cross-store roles) |
| 3 | Build permission mixins/decorators for each role | M2 | Peyton #1 | `@role_required('manager')`, `RolePermissionMixin` that checks `request.user.profile.role`; returns 403 on mismatch |
| 4 | Build login view in `accounts/views.py` (returns token + role + store) | M2 | Peyton #1 | `POST /api/auth/login/` returns `{token, user_id, role, store_id, first_name}` |
| 5 | Build registration view in `accounts/views.py` | M2 | Peyton #1 | `POST /api/auth/register/` creates account_user with token |
| 6 | Build logout view in `accounts/views.py` | M2 | Peyton #4 | `POST /api/auth/logout/` invalidates token |
| 7 | Build user management views (admin) | M2, M6 | Peyton #3, Curt #1 | Admin can list/create/edit/lock/unlock/delete users for their store only; super_admin can do it for all stores |
| 8 | Add role checks to all existing endpoints | M2 | Peyton #3 | Every endpoint returns 403 if role doesn't match; write a test per role per endpoint |
| 9 | Enforce store-scoping on querysets | M2 | Peyton #2 | Manager sees only their store's data; admin sees only their store; logistics_manager sees their region; super_admin sees all |

---

## Braxton — Inventory & Supply Hub

| Priority | Action Item | MUST | Blocked By | Definition of Done |
|---|---|---|---|---|
| 1 | Create inventory models in `inventory/models.py` | M3 | Gabe #1, Curt #2 | Models: `InventoryItem` (per-store), `HubInventoryItem` (per-hub), `SupplyTransfer`, `RestockAlert`; all with FKs to `Store`/`SupplyHub` |
| 2 | Create `SupplyUsageRecord` and `ImportHistory` models | M5 | Braxton #1 | Models match LLD §8.4.5: unique constraint on `(store, item_name, date)`, import log with status/error tracking |
| 3 | Run `makemigrations` and `migrate` for inventory app | M3 | Braxton #2 | All inventory tables exist, no errors |
| 4 | Build inventory CRUD views + serializers | M3 | Braxton #3, Peyton #3 | `GET/POST /api/inventory/items/`, `PATCH /api/inventory/items/<id>/`; scoped by role (manager=own store, logistics=region) |
| 5 | Build supply transfer CRUD views | M3 | Braxton #4 | `POST /api/inventory/transfers/` (create), `PATCH` (approve/deliver); hub inventory decrements atomically, store inventory increments on delivery |
| 6 | Build RestockAlert views | M3 | Braxton #4 | `GET /api/inventory/alerts/` (scoped by region for logistics_manager); alerts auto-created when inventory drops below threshold |
| 7 | Build CSV supply usage upload endpoint | M5 | Braxton #2, Peyton #3 | `POST /api/csv-imports/supply-usage/` validates per LLD §8.4.4 rules, upserts rows atomically, logs to `ImportHistory` |
| 8 | Build CSV import history endpoint | M5 | Braxton #7 | `GET /api/csv-imports/history/` returns past imports for the manager's region |
| 9 | Build logistics manager dashboard page | M6 | Braxton #4, #5, #6 | Dashboard shows: regional inventory grid, open restock alerts, pending transfers, hub inventory levels |

---

## Brock — Machine Maintenance & Repair

| Priority | Action Item | MUST | Blocked By | Definition of Done |
|---|---|---|---|---|
| 1 | Create maintenance models in `maintenance/models.py` | M4 | Gabe #1, Curt #1 | Models: `Machine`, `MachineStatusEvent`, `RepairAssignment`, `MaintenancePolicy`; all FKs to `Store` |
| 2 | Run `makemigrations` and `migrate` for maintenance app | M4 | Brock #1 | All maintenance tables exist, no errors |
| 3 | Build machine CRUD views + serializers | M4 | Brock #2, Peyton #3 | `GET /api/maintenance/machines/` (filtered by store/region based on role), `GET /api/maintenance/machines/<id>/` with status history |
| 4 | Build machine status update view | M4 | Brock #3 | `PATCH /api/maintenance/machines/<id>/status/` creates a `MachineStatusEvent`, updates `Machine.current_status`; validates status transitions |
| 5 | Build repair assignment CRUD views | M4 | Brock #3 | `GET/POST /api/maintenance/assignments/`; repair_staff can see their assignments; create assigns a repair_staff user to a machine at a store |
| 6 | Build CSV repair schedule upload endpoint | M5 | Brock #2, Peyton #3 | `POST /api/csv-imports/repair-schedules/` validates per LLD §8.5.3 rules, creates/updates Machine records and MachineStatusEvent entries |
| 7 | Implement 7-day error auto-escalation rule | M4 | Brock #4 | Machines in `error` status > 7 days auto-set to `out-of-order`; runs as management command or Celery periodic task |
| 8 | Build repair staff dashboard page | M6 | Brock #3, #5 | Dashboard shows: machines by status (filterable), assigned repairs, machines needing urgent attention (error/out-of-order) |

---

## Matthew — Orders & Payments

| Priority | Action Item | MUST | Blocked By | Definition of Done |
|---|---|---|---|---|
| 1 | Migrate existing Order/Drink/Revenue models to `orders/models.py` | M6 | Gabe #1, Curt #1 | Models moved from `backend/` to `orders/`; add `store` FK to Order; existing fields preserved |
| 2 | Migrate existing order/payment views to `orders/views.py` | M6 | Matthew #1, Peyton #3 | All order endpoints work from new app; role checks applied (account_user=own orders, manager=store orders, admin=store orders) |
| 3 | Migrate Stripe PaymentIntent view to `orders/views.py` | M6 | Matthew #1 | `POST /api/orders/create-payment-intent/` works; refund function accessible |
| 4 | Add store-scoping to order queries | M2, M6 | Matthew #2, Curt #1 | Orders are associated with a store; manager sees only their store's orders |
| 5 | Build manager dashboard — orders & revenue panel | M6 | Matthew #4, Peyton #3 | Manager dashboard shows: today's orders (pending/processing/completed), revenue summary, payment lookup |
| 6 | Build order cancellation + refund flow | M6 | Matthew #3 | `PATCH /api/orders/<id>/cancel/` changes status to cancelled, calls Stripe refund if PaymentStatus=paid, returns updated order |
| 7 | Ensure drink customization works end-to-end | M6 | Matthew #1 | Create drink → add to order → checkout → payment intent → order confirmed; all via API |

---

## Dependency Graph (What to Merge First)

```
Week 1 (unblocks everyone):
  Gabe #1-3  →  App skeletons + settings + root URLs
  Curt #1-3  →  Store/Region/SupplyHub models + migrations
  Peyton #1-3 → Role field + permission mixins

Week 2 (parallel work begins):
  Curt #4-8    →  All seed data commands + sample CSVs
  Peyton #4-9  →  Auth views + role enforcement
  Braxton #1-3 →  Inventory models + migrations
  Brock #1-2   →  Maintenance models + migrations
  Matthew #1-3 →  Migrate existing models/views to new app

Week 3 (features + dashboards):
  Braxton #4-9 →  Inventory views + CSV upload + logistics dashboard
  Brock #3-8   →  Machine views + CSV upload + repair dashboard
  Matthew #4-7 →  Store-scoped orders + manager dashboard panels
  Gabe #5-8    →  Notification views + super_admin/admin dashboards
  Peyton #7-9  →  User management + store-scoping enforcement
```

---

## Quick Stats

| Person | Total Items | Critical Path Items (Week 1) |
|---|---|---|
| **Gabe** | 8 | 3 (app skeletons, settings, URLs) |
| **Curt** | 9 | 3 (Store, Region, SupplyHub models) |
| **Peyton** | 9 | 3 (role field, store FK, permission mixins) |
| **Braxton** | 9 | 0 (starts Week 2 after models land) |
| **Brock** | 8 | 0 (starts Week 2 after models land) |
| **Matthew** | 7 | 0 (starts Week 2 after models land) |
| **Total** | **50 action items** | |
