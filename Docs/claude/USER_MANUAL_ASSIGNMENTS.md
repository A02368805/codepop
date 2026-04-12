# FloatStack User Manual — Team Assignments

**Status:** First Draft Review & Screenshot Capture

---

## Assignment Map

### Curt Reyes — Introduction, Getting Started, Account Features

**Sections:**

- `## Introduction`
- `## Getting Started`
- `## Account Features`

**Tasks:**

- [ ] Introduction:
  - [ ] Review text for clarity
  - [ ] Verify user type descriptions match actual code
  - [ ] Verify key features list is complete
- [ ] Getting Started:
  - [ ] Verify directions match actual UI (guest + account signup)
  - [ ] Add screenshots (4):
    - [ ] Home page with drink hero cards
    - [ ] Store selection page
    - [ ] Registration form
    - [ ] Login form
- [ ] Account Features:
  - [ ] Verify all 4 workflows (preferences, favorites, recommendations, order history)
  - [ ] Add screenshots (4):
    - [ ] Preferences page
    - [ ] Favorites page
    - [ ] Recommendations page
    - [ ] Order history page

---

### Braxton Edwards — Ordering, Admin User Management

**Sections:**

- `## Ordering as a Guest or Customer`
- `## Admin User Management`

**Tasks:**

- [ ] Ordering (all 8 steps):
  - [ ] Verify directions are accurate as guest
  - [ ] Verify directions are accurate as account user
  - [ ] Verify AI assistant step directions match actual UI
  - [ ] Add screenshots (7):
    - [ ] Stores page with geolocation option
    - [ ] Menu page with drink cards
    - [ ] Customization page
    - [ ] AI assistant chat interface
    - [ ] Cart page
    - [ ] Checkout page
    - [ ] Order confirmation page
  - [ ] Flag any missing features or inaccuracies
- [ ] Admin User Management:
  - [ ] Verify dashboard directions are accurate
  - [ ] Verify user CRUD operations match directions
  - [ ] Add screenshots (2):
    - [ ] Admin dashboard
    - [ ] User management table

---

### Brock McDermott — Logistics Manager Workflow, Getting Support

**Sections:**

- `## Logistics Manager Workflow`
- `## Getting Support`

**Tasks:**

- [ ] Logistics Manager Workflow:
  - [ ] Verify supply hub workspace accuracy
  - [ ] Verify transfer lifecycle (Approved → Reserved → Shipped → In Transit → Delivered → Received)
  - [ ] Verify transfer creation directions match actual UI
  - [ ] Verify AI supply schedule descriptions
  - [ ] Verify CSV import field names and validation rules
  - [ ] Add screenshots (8):
    - [ ] Logistics dashboard
    - [ ] Supply hub workspace
    - [ ] Transfer creation form
    - [ ] Transfer detail/approval view
    - [ ] Transfer progress/timeline
    - [ ] Supply schedules list
    - [ ] Supplier orders table
    - [ ] CSV import form
  - [ ] Check all URLs are correct
- [ ] Getting Support:
  - [ ] Verify support conversation flows match actual UI
  - [ ] Add screenshots (2):
    - [ ] Support home page
    - [ ] Support conversation detail

---

### Matthew Webecke — FAQs, Troubleshooting

**Sections:**

- `## FAQs`
- `## Troubleshooting`

**Tasks:**

- [ ] FAQs:
  - [ ] Review existing 10 FAQs for accuracy
  - [ ] Verify all answers match actual behavior
  - [ ] Expand with 4-5 new questions:
    - [ ] Questions about store selection & geolocation
    - [ ] Questions about pickup times/locations
    - [ ] Questions about ordering & customization
  - [ ] Improve FAQ answers with practical examples
- [ ] Troubleshooting:
  - [ ] Expand with 3-5 new payment/UI/ordering issues
  - [ ] Add solutions for common form errors
  - [ ] Verify error message text matches actual error states
  - [ ] Ensure troubleshooting covers geolocation issues

---

### Peyton — Manager Workflow, Super Admin System Overview

**Sections:**

- `## Manager Workflow`
- `## Super Admin System Overview`

**Tasks:**

- [ ] Manager Workflow:
  - [ ] Verify order queue directions are accurate (status grouping, transitions)
  - [ ] Verify inventory adjustment directions match actual inline UI
  - [ ] Add screenshots (3):
    - [ ] Manager dashboard
    - [ ] Order queue table
    - [ ] Inventory management table (with inline adjust)
- [ ] Super Admin System Overview:
  - [ ] Verify system-wide analytics directions are accurate
  - [ ] Verify sync health monitoring page directions match actual UI
  - [ ] Verify audit log visibility directions are accurate
  - [ ] Add screenshots (2):
    - [ ] Super admin dashboard
    - [ ] Sync workspace

---

### Gabriel Nielsen — Repair Staff Workflow, Contact & Feedback

**Sections:**

- `## Repair Staff Workflow`
- `## Contact & Feedback`

**Tasks:**

- [ ] Repair Staff Workflow:
  - [ ] Verify repair dashboard directions match actual UI
  - [ ] Verify urgent queue grouping described correctly
  - [ ] Verify assignment detail directions are accurate
  - [ ] Verify repair status CSV import field descriptions match actual form
  - [ ] Verify all maintenance/repair terminology
  - [ ] Add screenshots (4):
    - [ ] Repair dashboard
    - [ ] Maintenance workspace
    - [ ] Assignment detail view
    - [ ] CSV import form (repair status)
- [ ] Contact & Feedback:
  - [ ] Verify contact information is complete and accurate
  - [ ] Ensure support channels are correctly listed
  - [ ] Verify any feedback submission details

---

## How to Submit

1. **Update the manual directly** in `/home/curt/Code/codepop/Docs/User_Manual.md`
   - Replace screenshot placeholders (`📸 **Screenshot:** ...`) with actual image paths
   - Save screenshots to `/home/curt/Code/codepop/Docs/screenshots/` folder

2. **Check off completed tasks** in this assignment file

3. **Note any inconsistencies** or missing features at the end of your section

4. **Git flow:**

   ```bash
   git checkout -b user-manual/[your-name]
   # make changes
   git add Docs/User_Manual.md Docs/claude/USER_MANUAL_ASSIGNMENTS.md
   git commit -m "user manual: [section name] verified + screenshots"
   git push origin user-manual/[your-name]
   # open PR
   ```
