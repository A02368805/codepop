# Group 2 Execution Plan — Core Business Engine

## Objective
Ship Group 2 as the operational business engine on canonical foundations, with strict business logic ownership in canonical modules only.

## Scope Lock (Exact)
- Orders + checkout flow (guest + account)
- Payment orchestration and reconciliation
- Inventory reservation/deduction safety
- Supply hub transfer lifecycle + rule enforcement
- Supply usage CSV transactional pipeline
- Maintenance status CSV transactional pipeline
- AI hooks + async business jobs
- Canonical endpoint rule (no new business logic in legacy endpoints)

## Team Lanes (Suggested)
- **Lane A (Orders/Payments):** 2 engineers
- **Lane B (Inventory/Transfers):** 2 engineers
- **Lane C (Imports/AI/Async):** 2 engineers
- **Lane D (QA/Integration):** 1 engineer + shared support

---

## Phase Plan (Dependency Ordered)

## Phase 0 — Guardrails and Baseline (Day 1)
**Goal:** prevent scope drift and lock architectural rules.

### Tickets
- **G2-00.1** Freeze legacy logic paths and document canonical-only policy.
- **G2-00.2** Add CI/test checks to prevent new business logic in legacy endpoints.
- **G2-00.3** Define invariant checklist in code review template:
  - one order = one store
  - server-authoritative pricing
  - inventory cannot go negative
  - transfer rule enforcement
  - import is all-or-nothing + auditable

**Estimate:** 0.5–1 day
**Dependencies:** none

---

## Phase 1 — Orders and Checkout Core (Days 1–3)
**Goal:** complete order authority and checkout behavior.

### Tickets
- **G2-01.1** Cart mutations + HTMX partial updates (add/update/remove + totals refresh).
- **G2-01.2** Enforce one-order-one-store ownership rule in service layer.
- **G2-01.3** Guest and account-user checkout support through shared order creation flow.
- **G2-01.4** Server-side pricing validation at order commit and pre-payment intent.
- **G2-01.5** State machine guards for invalid transitions + cancellation/refund request behavior.

**Estimate:** 2–3 days
**Dependencies:** Phase 0
**Owner lane:** A

---

## Phase 2 — Payment Orchestration (Days 3–4)
**Goal:** authoritative payment records, safe reconciliation, refund path.

### Tickets
- **G2-02.1** PaymentIntent creation + client_secret response contract.
- **G2-02.2** Canonical PaymentTransaction creation/update flow tied to orders.
- **G2-02.3** Webhook verification stub with idempotent event handling.
- **G2-02.4** Payment reconciliation transitions with state safety checks.
- **G2-02.5** Refund workflow + ledger updates.

**Estimate:** 1.5–2 days
**Dependencies:** Phase 1
**Owner lane:** A

---

## Phase 3 — Inventory Reservation and Deduction Safety (Days 3–5)
**Goal:** guarantee no oversubscription or negative balances.

### Tickets
- **G2-03.1** Reserve/deduct inventory at queue commitment only.
- **G2-03.2** Add transactional locking around inventory mutation paths.
- **G2-03.3** Prevent oversubscription in concurrent checkout/queue operations.
- **G2-03.4** Threshold checks and alert trigger behavior.
- **G2-03.5** Add reversal behavior where cancellation/refund policy requires it.
- **G2-03.6** Race-condition test suite for contention scenarios.

**Estimate:** 2–3 days
**Dependencies:** Phase 1 (and payment completion behavior from Phase 2)
**Owner lane:** B

---

## Phase 4 — Supply Hubs and Transfers (Days 4–6)
**Goal:** complete transfer lifecycle and rule enforcement.

### Tickets
- **G2-04.1** Hub inventory balances and lifecycle entities finalized.
- **G2-04.2** Transfer lifecycle actions: create/approve/reserve/ship/deliver/receive.
- **G2-04.3** Same-region store transfer rule enforcement.
- **G2-04.4** Hub-source selection + 1000-mile cross-region hub rule enforcement.
- **G2-04.5** HTMX transfer actions wired to service transitions + validation feedback.
- **G2-04.6** Atomic source/destination reservation and receipt behavior.

**Estimate:** 2–3 days
**Dependencies:** Phase 3 primitives
**Owner lane:** B

---

## Phase 5 — CSV Import Pipelines (Days 4–6, parallel)
**Goal:** both import pipelines are transactional and auditable.

### Tickets
- **G2-05.1** Supply usage CSV: upload/parser/schema/row validation.
- **G2-05.2** Supply usage CSV transactional write + import history + errors.
- **G2-05.3** Maintenance status CSV: upload/parser/schema/row validation.
- **G2-05.4** Maintenance status transactional writes + auditable error reporting.
- **G2-05.5** Sample CSV fixtures + rollback-on-invalid-row tests.

**Estimate:** 2–3 days
**Dependencies:** Phase 0 only (can run in parallel with Phase 4)
**Owner lane:** C

---

## Phase 6 — AI Hooks and Async Jobs (Days 6–7)
**Goal:** business-event triggers and background processing are in place.

### Tickets
- **G2-06.1** Recommendation/forecast stubs wired to business events.
- **G2-06.2** Import-to-AI analysis triggers.
- **G2-06.3** Env-driven AI provider selection abstraction.
- **G2-06.4** Background job idempotency/retry safety checks.

**Estimate:** 1.5–2 days
**Dependencies:** Phase 5 (import triggers) and core domain events from Phases 2–4
**Owner lane:** C

---

## Phase 7 — Canonical Endpoint Rule Enforcement (continuous + Day 7 closeout)
**Goal:** no net-new business logic in legacy endpoints.

### Tickets
- **G2-07.1** Audit endpoint surface and compatibility adapters.
- **G2-07.2** Add tests/checks to block business-logic drift.
- **G2-07.3** Verify all new logic is in canonical modules and service layer.

**Estimate:** 0.5–1 day (continuous)
**Dependencies:** all phases
**Owner lane:** D + all lane leads

---

## Phase 8 — Exit Gate Validation (Day 8)
**Goal:** prove Group 2 is complete.

### Required pass criteria
- Checkout works end-to-end in dev mode.
- Payment records are created and tied correctly to orders.
- Inventory cannot go negative.
- Transfer rules are enforced.
- Both CSV pipelines are transactional and auditable.
- Background jobs process business tasks.
- No new business logic lives in legacy endpoints.

### Tickets
- **G2-08.1** Full integration run for guest and account checkout.
- **G2-08.2** Payment/order linkage and reconciliation assertions.
- **G2-08.3** Inventory contention/race scenario pass.
- **G2-08.4** Transfer rule matrix validation pass.
- **G2-08.5** Import pipeline valid/invalid fixture matrix pass.
- **G2-08.6** Async processing and retry behavior pass.
- **G2-08.7** Legacy-boundary check pass.

**Estimate:** 1 day
**Dependencies:** all feature phases complete
**Owner lane:** D

---

## Parallelization Map
- **Can run in parallel:** Phase 4 (Transfers) + Phase 5 (Imports)
- **Must precede others:** Phase 0
- **Critical chain:** Phase 1 → Phase 2 + Phase 3 → Phase 8
- **Continuous governance:** Phase 7 during all implementation

---

## Risk Register (Top)
1. **Concurrency oversubscription risk**
   - Mitigation: locking + race tests (G2-03.2, G2-03.6)
2. **Webhook double-processing risk**
   - Mitigation: idempotency key handling (G2-02.3)
3. **Legacy endpoint drift risk**
   - Mitigation: CI/test guardrails + PR checklist (G2-00.2, G2-07.2)
4. **Import partial-write risk**
   - Mitigation: all-or-nothing transaction tests (G2-05.5)

---

## Ready-to-Start First Sprint Slice (Day 1)
1. G2-00.1, G2-00.2, G2-00.3
2. G2-01.1, G2-01.2
3. G2-05.1 (in parallel)

If these 6 tickets are accepted by end of Day 1, Group 2 execution is on track.
