# Sprint Backlog Triage & User Story Mapping

## 1. Backlog Triage (MoSCoW)

### MUST — Demo-Critical (Sprint Goal)

These are the items that **must** be working for the sprint demo. If any of these are missing, the demo fails.

| # | Backlog Item | Owner | Why It's a MUST |
|---|---|---|---|
| **M1** | **Multi-store data model & seed data** — Create `Store`, `Region`, `SupplyHub` models. Seed 7 hubs, 20 Region C stores, 5+ stores per neighboring region, test users for every role. | Curt | Nothing else works without stores and roles in the database. Every other feature depends on this. |
| **M2** | **Role-based access control (7 roles)** — Implement `super_admin`, `admin`, `manager`, `logistics_manager`, `repair_staff`, `account_user`, `general_user` with permission enforcement on every endpoint. | Peyton | The requirements doc marks RBAC as (M) across 7+ functional requirements. Every dashboard and endpoint depends on role checks. |
| **M3** | **Logistics dashboard + inventory coordination** — `InventoryItem`, `SupplyHub`, `HubInventoryItem`, `SupplyTransfer`, `RestockAlert` models; logistics manager dashboard with regional inventory view; supply transfer workflow (hub → store, store → store). | Braxton | The entire Supply Hub section (LLD §5) is (M) in the requirements. Logistics manager is a new role with no existing implementation. |
| **M4** | **Machine maintenance tracking + repair dashboard** — `Machine`, `MachineStatusEvent`, `RepairAssignment`, `MaintenancePolicy` models; repair staff dashboard showing machine health by location; status tracking with the 7 defined statuses. | Brock | Machine maintenance tracking is (M) in the requirements. Repair staff is a new role with no existing implementation. |
| **M5** | **CSV import (supply usage + repair schedules)** — Upload endpoints for both CSV types; validation per LLD §8.4 and §8.5 rules; import history logging; data persisted to DB. | Braxton (supply) / Brock (repair) | Requirements doc: CSV import for supply usage and repair schedules are both (M). This is the primary data input mechanism for logistics and repair workflows. |
| **M6** | **Dashboards for all 5 staff roles** — `super_admin`, `admin`, `manager`, `logistics_manager`, `repair_staff` each get a role-appropriate dashboard displaying only their permitted data. | All (each person builds their role's dashboard) | Requirements doc explicitly marks dashboards for all 5 roles as (M). |

---

### SHOULD — Important, But Demo Survives Without It

| # | Backlog Item | Owner | Notes |
|---|---|---|---|
| S1 | AI-assisted supply usage analysis | Braxton | ReorderService, 30-day rolling averages, RestockAlert AI justification. Valuable but dashboard can show raw data without AI. |
| S2 | AI-assisted repair schedule optimization | Brock | Route optimization (nearest-neighbor + 2-opt), constraint-based scheduling. Dashboard can show machines without optimized routes. |
| S3 | Push notifications (FCM) | Gabe | Order-ready, low inventory, machine error alerts. Nice for demo polish, but core workflows function without push. |
| S4 | Geolocation-based drink preparation | Matthew | Proximity detection + countdown timer. The "I've Arrived" manual button is a sufficient fallback for demo. |
| S5 | Inter-store synchronization | Curt | REST-based sync, delta merging, version tracking. Critical for production, but demo can show individual store operation. |
| S6 | Supply routing optimization (1000-mile rule) | Braxton | Hub-to-store distance logic. Demo can show basic transfers without geographic constraints. |
| S7 | Alerts for low supplies / machine warnings | Braxton / Brock | Automated threshold-based alerts. Managers can check dashboards manually for demo. |
| S8 | Stripe webhook integration | Matthew | Real-time payment status updates. Current PaymentIntent + frontend redirect flow works for demo. |

---

### COULD — Nice-to-Have, If Time Allows

| # | Backlog Item | Owner | Notes |
|---|---|---|---|
| C1 | Drink rating system | Matthew | 1–5 star ratings feeding into AI recommendations. |
| C2 | Seasonal menu | Matthew | Dynamic menu updates for limited-time drinks. |
| C3 | Loyalty program | Peyton | Points system, rewards. |
| C4 | Social media sharing | — | Share drink creations externally. |
| C5 | Cross-region supply sharing recommendations | Braxton | AI suggesting transfers between regions. |
| C6 | Predictive maintenance recommendations | Brock | AI predicting failures before they happen. |
| C7 | Historical analytics dashboards | Gabe | Trend analysis for supply usage and repair activity. |
| C8 | Conflict resolution audit UI | Curt | Visual display of sync conflict logs. |

---

### WON'T — Not This Sprint

| # | Item | Reason |
|---|---|---|
| W1 | Global trend-based restocking | Requirements doc explicitly marks as Won't Have. |
| W2 | Shared accounts | Requirements doc explicitly marks as Won't Have. |
| W3 | Refunds after drink is made | Requirements doc explicitly marks as Won't Have. |
| W4 | Preloaded account balance / gift cards | Requirements doc explicitly marks as Won't Have. |
| W5 | Cash payments | Requirements doc explicitly marks as Won't Have. |
| W6 | Centralized global server | Contradicts the decentralized architecture requirement. |
| W7 | Real-time nationwide sync | Requirements doc explicitly marks as Won't Have. |
| W8 | Fully autonomous AI (no human approval) | Requirements doc explicitly marks as Won't Have. |
| W9 | Customer access to logistics/repair dashboards | Requirements doc explicitly marks as Won't Have. |
| W10 | Persistent data for general users | Requirements doc explicitly marks as Won't Have. |

---

## 2. MUST Items → User Story Mapping

Each MUST item is linked to specific user stories from the Requirements Document. User stories are referenced by role section and their original MoSCoW tag.

---

### M1: Multi-Store Data Model & Seed Data

| User Story | MoSCoW | Source Section |
|---|---|---|
| "The system must support multiple store locations across the United States." | (M) | Functional Req → Multi-Store & Distributed Architecture |
| "The system must support seven predefined supply hub regions." | (M) | Functional Req → Multi-Store & Distributed Architecture |
| "The system must include test data that creates: 7 supply hubs, 20 stores in Region C, at least 5 stores in each neighboring region, logistics_manager users, repair_staff users" | (M) | Functional Req → Test Data & Simulation |
| "The system must provide seed data files to automatically populate stores, supply hubs, machines, users, inventory, and roles for testing and validation purposes" | (M) | Functional Req → Test Data & Simulation |
| As an account_user, "I want to order drinks from any store location so that I can use the service wherever I travel." | (M) | User Stories → Account User |

---

### M2: Role-Based Access Control (7 Roles)

| User Story | MoSCoW | Source Section |
|---|---|---|
| "The system must support the following roles: super_admin, admin, manager, logistics_manager, repair_staff, account_user, general_user" | (M) | Functional Req → User Roles & Permissions |
| "Each role must have access only to the data and dashboards permitted by their role definition." | (M) | Functional Req → User Roles & Permissions |
| As a super_admin, "I want to access data for any store location so that I can investigate issues and oversee operations company-wide." | (M) | User Stories → Super Admin |
| As an admin, "I want to manage user accounts for my store only so that I can resolve account issues while maintaining data boundaries between locations." | (M) | User Stories → Admin |
| As an admin, "I want to add or remove manager permissions so that I can adjust staff access as roles change." | (M) | User Stories → Admin |
| As an account_user, "I want to sign in using secure authentication so that I can access my drink history and saved preferences." | (M) | User Stories → Account User |
| As a general_user, "I want to place orders without creating an account so that I can try the service without a registration barrier." | (M) | User Stories → General User |
| "All sensitive data must be encrypted in transit and at rest." | (M) | Non-Functional Req → Security |
| "Role-based access control must be strictly enforced." | (M) | Non-Functional Req → Security |

---

### M3: Logistics Dashboard + Inventory Coordination

| User Story | MoSCoW | Source Section |
|---|---|---|
| As a logistics_manager, "I want to manage supplies for stores in my assigned region so that inventory remains available and stores avoid stockouts." | (M) | User Stories → Logistics Manager |
| As a logistics_manager, "I want to view supply levels for all stores I manage so that I can identify which stores need restocking and prioritize deliveries." | (M) | User Stories → Logistics Manager |
| As a logistics_manager, "I want to coordinate supplies between local stores and regional supply hubs so that I can balance inventory across locations and reduce delivery costs." | (M) | User Stories → Logistics Manager |
| As a logistics_manager, "I want to route supplies from hubs to stores within 1000 miles so that stores outside my primary region can still receive timely restocking." | (M) | User Stories → Logistics Manager |
| "Supply hubs must be able to supply: stores in their own region, stores in other regions within 1000 miles" | (M) | Functional Req → Supply Hub & Inventory |
| "The system must track inventory levels at each store." | (M) | Functional Req → Supply Hub & Inventory |
| "Stores must be able to transfer supplies directly to other nearby stores when inventory is low." | (M) | Functional Req → Supply Hub & Inventory |
| As a manager, "I want to view inventory levels for my store (including ice cream freezer stock) so that I can verify stock availability." | (M) | User Stories → Manager |

---

### M4: Machine Maintenance Tracking + Repair Dashboard

| User Story | MoSCoW | Source Section |
|---|---|---|
| As repair_staff, "I want to manage machine repair schedules for the stores I am responsible for so that I can ensure all machines receive timely maintenance." | (M) | User Stories → Repair Staff |
| As repair_staff, "I want to track machine status across all assigned locations so that I can monitor equipment health and plan service visits." | (M) | User Stories → Repair Staff |
| As repair_staff, "I want to see machines that are out-of-order or in error status so that I can prioritize urgent repairs and minimize store downtime." | (M) | User Stories → Repair Staff |
| "The system must track machines at each store location." | (M) | Functional Req → Machine Maintenance |
| "Each machine must have: machine type, operational start date, current status, status date" | (M) | Functional Req → Machine Maintenance |
| "Supported machine statuses: normal, repair-start, repair-end, warning, error, out-of-order, schedule-service" | (M) | Functional Req → Machine Maintenance |
| "Machines must not be allowed to operate in unsafe or error states for more than 7 days without repair or shutdown." | (M) | Business Req → Reliability & Brand Protection |

---

### M5: CSV Import (Supply Usage + Repair Schedules)

| User Story | MoSCoW | Source Section |
|---|---|---|
| As a logistics_manager, "I want to import supply usage data from structured files so that I can update inventory records in bulk without manual data entry." | (M) | User Stories → Logistics Manager |
| As repair_staff, "I want to import machine repair data from structured files so that I can update maintenance records in bulk without manual entry." | (M) | User Stories → Repair Staff |
| "The system must include CSV import files for: supply usage data, repair schedules" | (M) | Functional Req → Test Data & Simulation |
| "CSV import formats must be clearly documented." | (M) | Non-Functional Req → Maintainability |
| "Validation of imported files before processing" | (M) | Functional Req → MoSCoW Must Have list |

---

### M6: Dashboards for All 5 Staff Roles

| User Story | MoSCoW | Source Section |
|---|---|---|
| "The system must provide dashboards for: super_admin, admin, manager, logistics_manager, repair_staff" | (M) | Functional Req → Dashboards |
| "Dashboards must reflect role-specific permissions and responsibilities." | (M) | Functional Req → Dashboards |
| "Dashboards must display only role-relevant information with labeled metrics and consistent navigation elements." | (M) | Non-Functional Req → Usability |
| As a super_admin, "I want to view supply, repair, and financial data across all regions and stores." | (M) | User Stories → Super Admin |
| As an admin, "I want to view user complaints so that I can address service issues." | (M) | User Stories → Admin |
| As an admin, "I want to track inventory costs and maintenance expenses so that I can monitor store profitability." | (M) | User Stories → Admin |
| As a manager, "I want access to revenue and payment reports so that I can track daily sales." | (M) | User Stories → Manager |
| As a manager, "I want to view user payments and look up transactions so that I can investigate payment disputes." | (M) | User Stories → Manager |

---

## 3. Summary

| Category | Count | Target |
|---|---|---|
| **MUST** | 6 | ✅ Within 3–6 range |
| **SHOULD** | 8 | Important, scheduled if capacity allows |
| **COULD** | 8 | Backlog for future sprints |
| **WON'T** | 10 | Explicitly excluded |

**Sprint Goal:** By the end of this sprint, a demo can show a multi-store CodePop system with 7 roles, 5 staff dashboards, working supply/inventory coordination, machine maintenance tracking, and CSV data import — all backed by realistic seed data.
