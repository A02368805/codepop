# Peer-Store Cross-Store Authentication — Show & Tell

## Feature Overview

Account users can log in at any store in the distributed network. A user created at Store A can authenticate at Store B by having Store B validate credentials directly against Store A—without duplicating accounts. This is peer-to-peer validation, not peer authentication.

---

## 6-Part Speaking Structure (60 seconds each)

### Part 1 — Business Context

**Speaker: [Person 1]** (60s)

**Key Points:**
- FloatStack operates beverage machines across multiple independent stores
- Problem: Each store has its own database and user system
- Customer pain point: Users had to create separate accounts at each store
- Solution: Enable one account to work across all stores
- Constraint: Keep stores independent (no central database needed)
- Benefit: Seamless cross-store experience without account duplication

### Part 2 — Architecture Decision

**Speaker: [Person 2]** (60s)

**Key Points:**
- Explain why NOT a centralized auth server (avoids single point of failure, complexity, new infrastructure)
- Introduce the peer-to-peer model: stores validate each other directly
- How it works: Store B asks Store A "Is this password valid?"
- Each store stays independent—keeps control of its own data
- Benefit: Decentralized architecture that still enables cross-store access
- Clarify: No third-party identity provider (that's what "peer" usually means, but we did something different)

### Part 3 — Backend Implementation

**Speaker: [Person 3]** (60s)

**Key Points:**
- Explain Django's authentication backend system (pluggable authenticators)
- Our PeerStoreAuthBackend is a second authenticator (fallback)
- Two-tier flow: Try ModelBackend (local password) first
- If that fails, ask peer stores to validate
- Show the code in `server/apps/users/backends.py`
- Walk through: requests.post() to `/peer-validate/`, pass email & password
- Explain the Host header fix (Docker networking issue we solved)
- Mention the has_usable_password() check (handles peer users on repeat logins)

### Part 4 — Security & API

**Speaker: [Person 4]** (60s)

**Key Points:**
- Security first: Need to verify peer stores are legitimate
- Introduce X-Sync-Token header (shared secret between stores)
- Explain why CSRF exempt but token-protected
- Show the endpoint in `server/apps/users/views.py` — PeerValidateView
- Walk through: Check token, check origin, authenticate locally, return user data
- Explain why we only allow ACCOUNT_USER role (staff roles stay store-local)
- Security best practice: Return valid=false without leaking user existence (doesn't say "wrong password")
- Mention: This prevents unauthorized stores from brute-forcing

### Part 5 — Database & Demo Data

**Speaker: [Person 5]** (60s)

**Key Points:**
- Data model: Users exist primarily at one store (account.a001@ was created at Store A)
- When user logs in at a different store, we provision them locally (with no usable password)
- This allows password-free re-authentication via peer validation
- Show the bootstrap process in `bootstrap_demo_data.py`
- Explain: We seed demo accounts at each store
  - `account.a001@floatstack.local` (Store A)
  - `account.b001@floatstack.local` (Store B)
  - `account.casey@floatstack.local` (shared across stores)
- Highlight: Staff roles (managers, admins) CANNOT login cross-store (store-local only)
- This preserves data isolation and permissions per store

### Part 6 — Live Demo

**Speaker: [Person 6]** (60s) — **LIVE DEMO**

**Demo Flow:**
1. Open Store A (8001) login page, log in as `account.a001@floatstack.local` / `FloatStack123!`
   - Show the browser console logging the auth flow
   - Console shows: ✅ checking db... found
   - Console shows: 🔄 querying peer store-a...
   - Console shows: ✅ peer validation SUCCESS

2. Navigate to Store B (8002), log in with THE SAME credentials
   - Same email: `account.a001@floatstack.local`
   - Same password: `FloatStack123!`
   - **Browser console shows:**
     - ⏳ checking db...
     - ❌ not found (user doesn't exist at Store B yet)
     - 🔄 server checking local database
     - 🔄 querying peer store-a... (asking Store A to validate)
     - ✅ peer validation SUCCESS! (Store A confirmed the password)
     - 📝 provisioning peer user in local db
     - ✨ authentication successful
   - **Terminal logs show the peer validation request/response**

3. Show the authenticated user view on Store B
   - Same account data, preferences synced from Store A

4. Run tests: Show all 16 passing tests (`make test`)

---

## Setup Instructions

### Quick Start

```bash
# Build and start multiple stores (Store A + B)
make multi-up

# Seed demo data across all stores
make multi-demo

# Open the browser
# Store A: http://127.0.0.1:8001/
# Store B: http://127.0.0.1:8002/
```

### Demo Credentials

Account users that work across **all stores** (peer):

- `account.a001@floatstack.local`
- `account.b001@floatstack.local`
- **Password:** `FloatStack123!`

### Running Tests

```bash
make test
```

All 17 tests pass (test_peer_store_auth.py), including:

- `PeerValidateView` endpoint security & validation
- `PeerStoreAuthBackend` fallback authentication
- Cross-store credential checks
- X-Sync-Token security
- Account user provisioning
- Preference synchronization
- Staff role isolation (managers can't federate)

---

## Key Commits

- **b19faf9e** — Implement peer-store cross-store authentication
- **6ae88c48** — Proxy login

---

## Technical Highlights

| Layer       | Component              | File                                                           |
| ----------- | ---------------------- | -------------------------------------------------------------- |
| **Auth**    | PeerStoreAuthBackend   | `server/apps/users/backends.py`                                |
| **API**     | PeerValidateView       | `server/apps/users/views.py`                                   |
| **Seeding** | Account user bootstrap | `server/apps/users/management/commands/bootstrap_demo_data.py` |
| **Config**  | Settings integration   | `server/config/settings/base.py`                               |
| **Tests**   | Peer-store auth tests  | `server/tests/test_peer_store_auth.py`                         |

---

## Timing & Pacing

| Segment | Time | Notes |
|---------|------|-------|
| Intro (Person 1) | 60s | Business context and motivation |
| Architecture (Person 2) | 60s | High-level design decisions |
| Implementation (Person 3) | 60s | Code walkthrough w/ backends.py |
| Security (Person 4) | 60s | Code walkthrough w/ views.py |
| Data (Person 5) | 60s | Data models and seeding |
| **Live Demo (Person 6)** | **120s** | Real login flow with console logs |
| **Total Speaking** | **6 minutes** | |
| Q&A | 2-3 min | Budget for questions |
| **Full Slot** | **~11 min** | |

## Why This Feature Stands Out

✅ **Complete:** All layers built and tested (auth, API, security, data)  
✅ **Distributed:** Demonstrates true peer-to-peer multi-store architecture  
✅ **Secure:** Token-based peer validation, no plaintext credential passing  
✅ **User-Facing:** Real demo with live console logging showing auth flow  
✅ **Well-Tested:** 17 tests, including peer-store validation scenarios

---

## Demo Preparation Checklist

- [ ] Start multi-store system: `make multi-up`
- [ ] Seed data: `make multi-demo`
- [ ] **IMPORTANT: Clear peer user from Store B** (so we can see the peer validation):
  ```bash
  docker compose -f docker-compose.multi.yml exec -e DJANGO_SETTINGS_MODULE=config.settings.dev web_b python manage.py shell << 'EOF'
  from django.contrib.auth import get_user_model
  User = get_user_model()
  # Delete the peer user so we can see peer validation on login
  User.objects.filter(email="account.a001@floatstack.local", role="account_user").delete()
  print("✓ Cleared peer user from Store B")
  EOF
  ```
- [ ] Open two browser windows/tabs side-by-side
  - Tab 1: Store A login page <http://127.0.0.1:8001/login/>
  - Tab 2: Store B login page <http://127.0.0.1:8002/login/>
- [ ] **Browser DevTools Setup (CRITICAL):**
  - [ ] Open DevTools on **both tabs** (F12 or Cmd+J)
  - [ ] Go to **Console tab** (not Network, not Elements)
  - [ ] Enable **"Preserve log"** checkbox (upper left of console)
  - [ ] Clear console before demo (`console.clear()` or click clear button)
  - [ ] **Size and position the windows so console is visible during login**
- [ ] Have terminal open showing server logs: `docker compose -f docker-compose.multi.yml logs web_b -f`
- [ ] **Practice the demo flow** (with cleared Store B database):
  1. **Store A login** → console shows:
     - ⏳ checking db... ✅ found (with usable password)
     - (No peer validation needed - local password works)
  2. **Switch to Store B login** (with SAME credentials) → console shows:
     - ⏳ checking db... ❌ not found
     - 🔄 querying peer store-a...
     - ✅ peer validation SUCCESS
     - 📝 provisioning peer user
     - ✨ authentication successful
  3. Show authenticated user view at Store B (same name, preferences, etc.)
  4. **Terminal output** shows the peer HTTP request/response
- [ ] Have tests ready: `make test` command in another terminal
- [ ] Keep code files open in editor for speaker transitions (Parts 3, 4, 5)
