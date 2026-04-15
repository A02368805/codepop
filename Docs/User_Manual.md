# FloatStack User Manual

**Version:** 1.0 (Draft)
**Last Updated:** April 2026

---

## Table of Contents

1. [Introduction](#introduction)
2. [Getting Started](#getting-started)
3. [Ordering as a Guest or Customer](#ordering-as-a-guest-or-customer)
4. [Account Features](#account-features)
5. [Manager Workflow](#manager-workflow)
6. [Admin User Management](#admin-user-management)
7. [Logistics Manager Workflow](#logistics-manager-workflow)
8. [Repair Staff Workflow](#repair-staff-workflow)
9. [Super Admin System Overview](#super-admin-system-overview)
10. [Getting Support](#getting-support)
11. [Troubleshooting](#troubleshooting)
12. [FAQs](#faqs)
13. [Contact & Feedback](#contact--feedback)

---

## Introduction

### What is FloatStack?

FloatStack is a web-based ordering platform for custom sodas and floats. Customers browse drink menus, customize beverages to their taste, and place orders for pickup at local stores. Store managers handle order fulfillment, inventory management, and daily operations. Logistics coordinators oversee supply distribution across multiple locations. Repair staff track machine maintenance.

### Who Can Use FloatStack?

FloatStack serves seven user types:

| User Type | Who They Are | What They Do |
|---|---|---|
| **Guest** | One-time customer, no account | Browse stores, order online, look up order via code |
| **Account User** | Registered customer | Order, save favorites, get recommendations, manage preferences |
| **Manager** | Store staff | Queue orders, manage inventory, adjust stock |
| **Admin** | Store administrator | Manage users, handle admin tasks |
| **Logistics Manager** | Regional coordinator | Manage supply transfers, approve orders, oversee inventory |
| **Repair Staff** | Maintenance technician | Schedule repairs, track machine health |
| **Super Admin** | System administrator | System-wide oversight, user management, analytics |

### Key Features Overview

- **Drink Customization** — choose base soda, syrups, add-ins, ice cream
- **AI-Assisted Ordering** — get recommendations based on preferences or chat with an assistant
- **Order Tracking** — know when your drink is ready
- **Favorites & Preferences** — save custom drinks, store taste preferences
- **Inventory Management** — staff can track stock and adjust levels
- **Supply Coordination** — logistics manage transfers between stores and hubs
- **Machine Maintenance** — repair staff schedule and track service

---

## Getting Started

### For Guests (One-Time Customers)

**No account needed.** Guests can order immediately.

1. Go to `http://[floatstack-url]/`
   > 📸 **Screenshot:** FloatStack home page with drink hero cards and "Start Ordering" button

2. **Find a Store**
   - Click "Start Ordering" or go to `/stores/`
   - Allow browser location access for nearest-store recommendation, or manually select a store from the list
   > 📸 **Screenshot:** Store selection page with map view and list view

3. **Browse the Menu**
   - You're now in the drink menu for your chosen store
   - Featured menu items appear as cards (e.g., "Vanilla Sunset," "Cache Float")
   > 📸 **Screenshot:** Menu page with drink cards, size selector, hero section

4. **Customize Your Drink** (see [Ordering as a Guest or Customer](#ordering-as-a-guest-or-customer) below)

### For New Account Users

**Creating an Account:**

1. Go to `/register/`
2. Enter:
   - Email address
   - Password (must be at least 8 characters)
   - Confirm password
3. Click "Create Account"
4. Log in with your email and password

> 📸 **Screenshot:** Registration form with email, password, confirm password fields

**Logging In:**

1. Go to `/login/`
2. Enter your email and password
3. Click "Log In"
4. You'll be redirected to your dashboard

> 📸 **Screenshot:** Login form with email and password fields

---

## Ordering as a Guest or Customer

### Step 1: Browse Stores

1. Start at `/stores/`
2. (Optional) Allow browser location — FloatStack will show nearby stores first
3. Click on a store to begin ordering

> 📸 **Screenshot:** Stores page with map and store list, geolocation option

### Step 2: Browse the Menu

Once you've selected a store, you'll see the drink menu at `/orders/menu/<store>/`

**Menu sections:**
- **Featured items** — popular or new drinks (shown at top)
- **All menu items** — complete drink catalog, organized by type

**For each drink:**
- Name and price (prices vary by size: Small, Medium, Large)
- Badge (e.g., "Popular," "Signature," "New")
- Quick preview or customization button

> 📸 **Screenshot:** Menu page showing drink cards with prices, size toggles, "Customize" button

### Step 3: Customize Your Drink

Click on any drink to customize it:

1. **Choose a Size:** Small, Medium, Large (affects price)
2. **Pick a Base Soda** (required)
   - Examples: Coke, Sprite, Root Beer, Cream Soda, Mountain Dew, Pepsi
3. **Add Syrups** (optional, $0.25–$0.30 each)
   - Fruit: Strawberry, Cherry, Raspberry, Mango, etc.
   - Dessert: Caramel, Vanilla, Butterscotch, etc.
   - Citrus: Lime, Lemon, Orange, etc.
4. **Add Extras** (optional)
   - Cream, Whipped cream, Ice cream scoops
   - Fresh mint, citrus wedges
   - Purees
5. **Special Requests** (optional text field)
   - Any notes or allergies
6. **Review Price**
   - Total updates as you customize
7. Click **"Add to Cart"**

> 📸 **Screenshot:** Customization page with size selector, soda dropdown, syrup checkboxes, add-ins, notes field, price summary, Add to Cart button

### Step 4: Use AI Assistance (Optional)

**For Account Users Only:** Save AI recommendations for future orders.
**For Guests:** Use the assistant but won't be able to save the build.

**Option A: AI Chat Assistant**
- Click "Ask an Assistant" button on the menu
- Describe what you want in plain English (e.g., "I like fruity, sweet drinks")
- The assistant suggests flavor combinations
- Click a suggestion to add it to your cart

> 📸 **Screenshot:** AI assistant chat box with sample responses and "Add to Cart" button

**Option B: Get Recommendations (Account Users)**
- Go to `/orders/recommendations/`
- AI personalizes suggestions based on your taste preferences
- Click a recommendation to customize further or add to cart

> 📸 **Screenshot:** Recommendations page with personalized drink cards and "Customize" / "Add to Cart" buttons

### Step 5: Review Your Cart

1. Go to your cart (link in top navigation or click the cart icon)
2. You'll see all items you've added
3. For each item:
   - View the customization summary (base, syrups, add-ins)
   - Click the quantity field to update how many
   - Click "Remove" to delete the item from cart
4. See your **subtotal** at the bottom
5. Click **"Proceed to Checkout"**

> 📸 **Screenshot:** Cart page with cart items table (drink summary, quantity, remove button), subtotal, "Proceed to Checkout" button

### Step 6: Checkout

1. **For Guests:** Enter your contact info
   - Full Name
   - Phone Number
   - Email Address (for order updates)

2. **For Account Users:** Logged-in info is already filled

3. **Review Order Total**
   - Subtotal of all items
   - Final total displayed

4. **Choose Payment Method** (if applicable)
   - Credit/debit card via Stripe (or demo mock payment)

5. Click **"Place Order"**

> 📸 **Screenshot:** Checkout page with contact form (guest), order summary, total, payment button

### Step 7: Order Confirmation

After checkout, you'll see your **order confirmation page** with:
- **Order Code** (e.g., `FS-M5K9TD`) — save this to look up your order later
- **Pickup Combo** (e.g., `624`) — staff uses this to identify your order
- **Estimated Pickup Time**
- **Store Location** and hours

> 📸 **Screenshot:** Confirmation page with order code, pickup combo, store address, estimated time

### Step 8: Track Your Order

**As a Guest:**
1. Go to `/orders/lookup/`
2. Enter your:
   - Order Code (e.g., `FS-M5K9TD`)
   - Pickup Combo (e.g., `624`)
   - Guest Lookup Code (provided in confirmation email)
3. Click "Look Up Order"
4. You'll see the current status (Queued, Preparing, Ready for Pickup, Picked Up)

> 📸 **Screenshot:** Guest lookup form with order code, pickup combo, guest code fields

**As an Account User:**
1. Go to `/orders/history/`
2. All your past and current orders are listed with status
3. Click on any order to see details

> 📸 **Screenshot:** Order history page with list of orders, dates, statuses, "View Details" links

---

## Account Features

### Update Your Taste Preferences

Account users can help FloatStack personalize recommendations:

1. Log in and go to `/account/preferences/`
2. **Sweetness Preference** — select Light, Balanced, Sweet, or Extra Sweet
3. **Adventurousness** — select Classic (familiar flavors), Balanced, or Adventurous
4. Click **Save**

> 📸 **Screenshot:** Preferences page with sweetness and adventurousness radio buttons, Save button

### Save Favorite Drinks

After customizing a drink you love:

1. On the customization page, check **"Save as Favorite"**
2. Enter a nickname (optional, e.g., "My Summer Go-To")
3. Click **"Add to Cart and Save"**

Go to `/orders/favorites/` anytime to:
- See all your saved custom drinks
- Click a favorite to add it to your cart (same customization applied)
- Click the trash icon to remove a favorite

> 📸 **Screenshot:** Favorites page with saved drinks, customization summary, Add to Cart and Remove buttons

### Get Personalized Recommendations

1. Log in and go to `/orders/recommendations/`
2. AI learns from your taste preferences and order history
3. View drink suggestions tailored to you
4. Click any recommendation to customize further or add to cart

> 📸 **Screenshot:** Recommendations page with drink cards, "Customize" and "Add to Cart" buttons

### View Order History

1. Log in and go to `/orders/history/`
2. See all past orders with dates and totals
3. Click an order for full details (items ordered, customizations, price, status)

> 📸 **Screenshot:** Order history list, and detailed order view

---

## Manager Workflow

### Accessing the Manager Dashboard

1. Log in with a manager account
2. After logging in, you'll be redirected to `/dashboards/manager/`

![Manager Dashboard](diagrams/Manager_Dashboard.png)

### View the Order Queue

1. From the manager dashboard, click **"Open order queue"** or go to `/orders/`
2. You'll see all orders for your store, grouped by status:
   - **Queued** — orders waiting to start
   - **Preparing** — orders being made
   - **Ready** — orders ready for pickup
   - **Picked Up** — completed orders

![Order Queue](diagrams/Order_Queue.png)

### Process an Order

1. Click on an order in the queue
2. Review the customizations and special requests
3. **Mark as Preparing:** Click "Start Preparing" when you begin making the drink
4. **Mark as Ready:** Click "Ready for Pickup" when complete
5. **Mark as Picked Up:** Click "Picked Up" when the customer takes the order

![Process Order](diagrams/Process_Order.png)

### Manage Inventory

1. From the manager dashboard, click **"Inventory"** or go to `/inventory/`
2. You'll see a table of all inventory items for your store with:
   - Item name and unit
   - On-hand quantity
   - Reserved quantity (allocated to orders)
   - Adjust button

![Manager Inventory](diagrams/Manager_Inventory.png)

3. **Adjust Stock:**
   - Click on an item
   - Under the "Adjust" section of the item click into the field box to change the quantity or in the Amount field box
   - Enter the new on-hand count
   - Provide a reason for the adjustment
   - Click **"Save"** — the system updates immediately

![Adjust Stock](diagrams/Adjust_Stock.png)

---

## Admin User Management

### Accessing the Admin Dashboard

1. Log in with an admin account
2. You'll be redirected to `/dashboards/admin/`

> 📸 **Screenshot:** Admin dashboard with user management section

### Manage Users for Your Store

1. Go to `/admin/users/`
2. You'll see a list of all users assigned to your store

> 📸 **Screenshot:** Admin user management table with user names, roles, status, action buttons

3. **Add a New User:**
   - Click **"Add User"** button
   - Enter email, select role (Manager, Admin, Repair Staff)
   - Set initial password
   - Click **"Create"**

4. **Update a User:**
   - Click on a user in the list
   - Change their role, status (Active, Locked, Disabled), or password
   - Click **"Save"**

5. **Disable/Lock a User:**
   - Click on the user
   - Change status to "Locked" or "Disabled"
   - Click **"Save"** — user can no longer log in

> 📸 **Screenshot:** User update form with email, role, status, password fields

---

## Logistics Manager Workflow

### Accessing the Logistics Dashboard

1. Log in with a logistics manager account
2. You'll be redirected to `/dashboards/logistics/`

> 📸 **Screenshot:** Logistics dashboard with supply hub summary, transfer alerts, schedule approvals

### Manage Supply Hubs

1. From the logistics dashboard, click **"Supply Hubs"** or go to `/supply-hubs/`
2. You'll see a workspace with:
   - Hub inventory summary
   - Pending supply transfer requests
   - AI-generated supply schedules awaiting approval
   - Supplier order management

> 📸 **Screenshot:** Supply hub workspace with inventory, transfers, schedules, supplier orders panels

### Create a Supply Transfer

1. In the supply hub workspace, click **"Create Transfer"**
2. **Select Source:**
   - Sending store or hub (dropdown)
3. **Select Destination:**
   - Receiving store or hub (dropdown)
4. **Add Items:**
   - Click **"Add Item"** for each product to transfer
   - Enter item name and quantity
5. **Review Total:**
   - System shows what's available to send
6. Click **"Create Transfer"**

> 📸 **Screenshot:** Transfer creation form with source/destination dropdowns, item rows, Create button

### Approve a Transfer

1. In the supply hub workspace or at `/supply-hubs/transfers/`, find a pending transfer
2. Review the items and quantities
3. Click **"Approve"**
4. Transfer moves to "Approved" status and is ready to ship

> 📸 **Screenshot:** Transfer detail with items table, approval button, status indicator

### Track Transfer Progress

Transfer lifecycle:
1. **Approved** — admin has approved the request
2. **Reserved** — items are held aside at the source
3. **Shipped** — items left the source location
4. **In Transit** — transfer is on its way
5. **Delivered** — items arrived at destination
6. **Received** — destination has confirmed receipt

> 📸 **Screenshot:** Transfer progress timeline or status column in transfer table

### Approve AI-Generated Supply Schedules

1. Go to `/supply-hubs/schedules/`
2. You'll see proposed restock schedules created by AI based on usage patterns
3. Review each schedule:
   - Item name
   - Recommended quantity
   - Frequency (daily, weekly, monthly)
4. Click **"Approve"** to activate the schedule, or **"Edit"** to adjust quantities

> 📸 **Screenshot:** Supply schedules list with item, quantity, frequency, approve/reject buttons

### Manage Supplier Orders

1. Go to `/supply-hubs/supplier-orders/`
2. Create or view bulk orders from external suppliers:
   - **Create Order:** Enter items, quantities, and supplier
   - **Receive Order:** Mark delivery received
   - **Cancel Order:** Cancel if needed

> 📸 **Screenshot:** Supplier orders table with order number, items, status, action buttons

### Upload CSV Imports (Supply Usage)

1. Go to `/imports/`
2. Click **"Import Supply Usage"**
3. Upload a CSV file with columns:
   - Store ID
   - Item Name
   - Quantity Used
   - Date
4. System validates the file
5. Approved entries update inventory usage records

> 📸 **Screenshot:** CSV upload form with file selector, validation message, import button

### View Analytics

1. Go to `/analytics/`
2. You'll see cross-store reports:
   - Revenue by store and region
   - Usage trends
   - Machine failure rates
   - Supply health

> 📸 **Screenshot:** Analytics dashboard with charts and tables

---

## Repair Staff Workflow

### Accessing the Repair Dashboard

1. Log in with a repair staff account
2. After sign-in, you should land on the **Repair Dashboard**
3. Confirm the top navigation includes **Dashboard**, **Maintenance**, and **Imports**

![Repair dashboard with urgent machine alerts, upcoming assignments, and regional overview](screenshots/MaintenanceDash.png)

### View Maintenance Assignments

1. Open **Maintenance** from the top navigation (or click **Open machine queue** on the dashboard)
2. In the maintenance workspace, review:
   - **Urgent Queue** — machines needing immediate service
   - **Route-Aware Queue** — grouped city/route batches for dispatch planning
   - **Repair Assignments** — active and recent tasks assigned to you

![Maintenance workspace with urgent queue, assignment cards, and route-aware grouping](screenshots/RoutesDash.png)

### Complete a Repair Assignment

1. In **Repair Assignments**, open the assignment card you are working
2. Confirm key details:
   - Store and machine
   - Assignment and machine status
   - Route batch and latest activity notes
3. Add an update note if needed in the note box
4. Use the appropriate action button for the current state:
   - **Acknowledge**
   - **Start repair**
   - **Save update**
   - **Block**
   - **Complete**
   - **Close assignment** (when available)
5. Confirm the card updates and your latest activity appears in the assignment history line

![Repair assignment card with machine info, status, notes, and action buttons](screenshots/MaintenanceAssign.png)

### Upload CSV Imports (Repair Status)

1. Open **Imports** from the top navigation (or click **Import maintenance CSV** on the repair dashboard)
2. In the imports workspace, use the **Maintenance status CSV** card
3. Choose your CSV file and click **Import maintenance CSV**
4. Use the required header row exactly:
   - `store_address,machine_type_code,machine_operational_from_date,machine_status,status_date`
5. Confirm the job result in import history (queued, succeeded, or failed with validation details)

![Repair status CSV import form](screenshots/CSVupload.png)

---

## Super Admin System Overview

### Accessing the Super Admin Dashboard

1. Log in with a super admin account
2. You'll be redirected to `/dashboards/super-admin/`

![Super Admin Dashboard](diagrams/SuperAdmin_Dashboard.png)

### Monitor System Health

1. From the super admin dashboard, you have access to:
   - **Full Analytics** — revenue, usage, machine health across all stores and regions
   - **Sync Status** — real-time view of data synchronization between stores
   - **User Oversight** — all users, their roles, store assignments
   - **Audit Logs** — record of staff actions for compliance

2. Go to `/sync/` to view:
   - Pending sync events
   - Failed sync attempts
   - Conflict resolution status

![Sync Workspace](diagrams/Sync_Workspace.png)

### Manage System Users

1. Go to admin panel and use user management tools
2. Create, edit, or disable any user across all stores
3. Assign users to stores or regions
4. Set roles and permissions

---

## Getting Support

### Start a Support Conversation

1. Go to `/support/` from anywhere in FloatStack
2. Click **"Start New Conversation"**
3. Choose a topic or describe your issue in the message box
4. Click **"Send"**

> 📸 **Screenshot:** Support home with conversation list and "Start New Conversation" button

### Escalate an Issue

If your issue needs urgent attention:

1. From your support conversation
2. Click **"Escalate"**
3. Your issue is flagged for priority review

---

## Troubleshooting

### Common Issues and Solutions

**"I forgot my password"**
- Click "Forgot Password?" on the login page
- Enter your email
- Check your email for a password reset link

**"My order status isn't updating"**
- Refresh the page (browser refresh or press F5)
- If ordering as a guest, verify you're using the correct order code and guest lookup code

**"I can't add a drink to my cart"**
- Ensure you've completed all required fields (size, base soda)
- Check that you've selected a valid store
- Clear your browser cache and try again

**"Inventory adjustment didn't save"**
- Verify you have manager or admin permissions
- Ensure the new quantity is a valid number
- Check your internet connection and retry

**"My AI recommendation won't save"**
- Account users can save recommendations — are you logged in?
- Check that your account is active and not locked

**"I received an error during checkout"**
- Verify all form fields are filled correctly
- Check your internet connection
- Try a different browser or clear cache

**"Supply transfer is stuck in 'Approved' status"**
- Confirm the source has sufficient inventory reserved
- Check if destination location has space for the items
- Retry the transfer operation

---

## FAQs

**Q: Can I order as a guest without creating an account?**
A: Yes. Guests can browse stores, customize drinks, and checkout without an account. You'll receive an order code to look up your order later.

**Q: How do I save my favorite drink combination?**
A: Create an account, customize your drink, and check "Save as Favorite" before adding to cart. You can later quickly add it again from your favorites list.

**Q: How long does drink preparation take?**
A: Estimated times vary by store and current queue. You'll see the estimate on your confirmation page. Typical preparation is 5–10 minutes.

**Q: Can managers see all stores' orders or just their own?**
A: Managers see orders for their assigned store only. Super admins and logistics managers have cross-store visibility.

**Q: How do I know if an inventory item is low?**
A: The system alerts managers and logistics coordinators when inventory drops below configurable thresholds. Restock alerts appear in the logistics dashboard.

**Q: Can I cancel my order?**
A: Yes, if the order hasn't started being prepared. Go to your order detail page and click "Cancel Order." Refunds are processed according to the payment method.

**Q: What happens if I order something that runs out of stock?**
A: The system prevents ordering items that are out of stock. If an item is allocated to your order but runs out during preparation, staff will contact you to suggest alternatives.

**Q: How do supply transfers work?**
A: Transfers move inventory from one store/hub to another. Logistics managers create requests, approvals are made, items are reserved, shipped, and delivered between locations.

**Q: Can repair staff work on machines outside their assigned region?**
A: Repair staff are assigned to specific regions and stores. Cross-region assignments require super admin or logistics manager coordination.

**Q: Where can I see my entire order history?**
A: Account users can go to `/orders/history/` to see all past and current orders.

---

## Contact & Feedback

For support issues, bugs, or feature requests:

- **In-App Support (Primary):** Use **Help** in the app to start a support conversation and submit a follow-up request.
- **Demo Escalation Email (Demo Only):** `support@floatstack.demo` (for presentation/testing use; not a production inbox).
- **Repair Staff Operational Issues:** Report through your manager/super admin workflow and include store, machine, assignment context, and screenshots.
- **Bug Reports / Feature Feedback:** Submit through your team’s standard tracker with clear reproduction steps and expected vs actual behavior.

---

## Appendix: Demo Credentials

For testing or onboarding:

| Role | Email | Password |
|---|---|---|
| Customer | `account.casey@floatstack.local` | `FloatStack123!` |
| Customer | `account.river@floatstack.local` | `FloatStack123!` |
| Manager | `manager.c001@floatstack.local` | `FloatStack123!` |
| Admin | `admin.c001@floatstack.local` | `FloatStack123!` |
| Logistics Manager | `logistics.c@floatstack.local` | `FloatStack123!` |
| Repair Staff | `repair.north@floatstack.local` | `FloatStack123!` |
| Super Admin | `superadmin@floatstack.local` | `FloatStack123!` |

**Demo Guest Order Lookup:**
- Order Code: `FS-M5K9TD`
- Pickup Combo: `624`
- Guest Lookup Code: `GST-DEMO-001`

---

**End of User Manual (Draft)**

---

## Notes on Documentation Inconsistencies Found

The following inconsistencies between the High-Level Design (HLD) / Low-Level Design (LLD) docs and the actual codebase should be addressed:

1. **"general_user" role does not exist** — Both HLD and LLD describe a `general_user` role separate from `account_user`. The actual code has no such role. Guest behavior is handled via session-based carts and `GuestOrderContact` model. This manual uses "guest" instead of "general_user" to match the code.

2. **LLD URL namespace inconsistency** — LLD shows `/users/...` as URL prefix. Actual routes are at root (`/login/`, `/register/`, `/dashboard/`). Corrected in this manual.

3. **Order workspace role access** — LLD implies all staff can access `/orders/` queue. Code restricts access to `manager` and `super_admin` only. Clarified in the manager section.

4. **AI save functionality** — Guests can use the AI assistant chat but cannot save results. Only account users can save recommended builds. Noted in the "Account Features" section.

**Recommendation:** Align HLD/LLD documentation with the actual code to prevent future confusion during handoff or maintenance.
