# CodePop – High-Level Design Document

Version: Expanded Draft  
Project: CodePop 2026  
Document Type: High-Level Design (HLD)  
Status: Revised and Expanded

---

## 1. Introduction

### Purpose

This High-Level Design document defines the overall architecture, major components, system boundaries, operational responsibilities, and key design decisions for the CodePop 2026 platform.

CodePop is an AI-assisted soda and float ordering platform that began as a base web application focused on core ordering and customer interaction. For the 2026 project scope, the platform is extended into a **multi-store nationwide system** that supports decentralized operations, regional supply coordination, machine maintenance tracking, role-specific dashboards, and AI-assisted operational decision support.

The purpose of this document is to:

- describe the target system architecture at a level appropriate for planning, implementation, and review
- preserve continuity with the provided base webapp while clarifying how the system is being extended
- define major architectural decisions so that implementation work can proceed with minimal ambiguity
- provide a shared technical reference for the team, instructors, and future contributors
- establish boundaries between high-level architecture decisions and lower-level implementation details

This document emphasizes **what the system is, how its major parts fit together, and why those choices were made**. It does not attempt to fully specify internal algorithms, framework configuration, or endpoint-by-endpoint implementation details; those belong in the Low-Level Design document.

---

### Scope

This design covers the core CodePop platform and the major extensions required for the Spring 2026 project, including:

- extension of the provided base webapp into a multi-store platform
- nationwide support for many stores across the United States
- decentralized operation without a centralized global server
- store-level autonomy with regional coordination
- support for seven supply hubs with defined regional assignments
- support for local suppliers as replenishment sources
- store-to-store coordination within a region
- machine maintenance tracking at each location
- CSV-based operational data import with validation
- AI-assisted supply analysis and repair scheduling
- role-based dashboards and role-specific permissions
- customer ordering for both account users and general users
- payment processing through an external payment provider
- push notifications and geolocation-assisted store recommendations
- containerized deployment and distributed infrastructure planning
- test-data expectations required to populate and validate the system

This design intentionally excludes detailed database column definitions, exact Django model declarations, endpoint payload schemas, background job wiring, and framework-specific implementation code.

---

### Audience

This document is intended for:

- software developers implementing the system
- instructors and evaluators reviewing the architecture
- project stakeholders and team members
- developers using Codex or similar tools to generate implementation scaffolding
- future maintainers who need to understand the intended system boundaries and responsibilities

---

### Relationship to the Provided Base Webapp

CodePop is not being designed as a greenfield application. The team was given a base webapp and is required to extend it.

Accordingly, this High-Level Design assumes the following:

- the base application already provides a foundational web experience for customers and internal users
- some degree of ordering, authentication, and UI structure already exists
- the project objective is to **extend and reorganize the system**, not discard all previous work
- existing working flows should be preserved where reasonable and refactored only when needed to support the new requirements

This HLD therefore describes both:

1. the **target architecture** for the expanded CodePop system, and  
2. the **architectural direction** for evolving the current webapp into that target architecture.

The class implementation may simulate decentralized behavior within a single deployed application for practical reasons, but the architecture described here still reflects the intended distributed operational model.

---

## 2. System Overview

### Problem Statement

Dirty soda and float ordering involves a high degree of customer customization, time sensitivity, and operational dependency on supplies and specialized equipment. As CodePop expands beyond a single-location workflow, the platform must support many stores, each with its own operational state, while still enabling coordinated logistics and maintenance.

A traditional centralized architecture creates a single point of failure and can make regional operations brittle if the central system becomes unavailable. It also does not align with the project requirement that stores must function independently without relying on a centralized global server.

At the same time, purely isolated stores would make it difficult to:

- monitor inventory risk across nearby locations
- coordinate supply movement between stores and hubs
- optimize machine maintenance across many stores
- provide system-wide oversight for privileged roles
- preserve consistent operational standards nationwide

The platform must therefore balance **independence and coordination**.

The system must:

- support many stores across the USA
- avoid dependence on a centralized global server
- allow each store to continue operating independently during disconnection
- coordinate operational data regionally where required
- support seven supply hubs with defined coverage regions
- support local supplier and store-to-store replenishment workflows
- track machine status and repair schedules per location
- enforce strict role-based access control and clear responsibility boundaries
- provide dashboards aligned with each role’s operational responsibilities

---

### Proposed Solution

CodePop provides a **distributed, AI-assisted ordering and operations platform** built around a regional multi-node design.

Customers interact with CodePop through a responsive web interface. From the customer perspective, the platform provides:

- drink customization and ordering
- support for guest checkout and account-based ordering
- location-aware or time-based store selection
- order tracking and notifications
- account-based preferences, favorites, and drink recommendations

Operationally, the system is organized around **store nodes**, **regional supply hubs**, and **role-scoped management views**.

Each store is treated as an independent operational node responsible for:

- local order handling
- local payment lifecycle tracking
- local inventory ownership
- local machine records
- local operational continuity during temporary disconnection

Stores coordinate with:

- other nearby stores in the same region for supply visibility and transfer support
- a designated regional supply hub
- eligible cross-region hubs within 1000 miles when needed
- repair staff assigned to their region and locations

The system includes the following roles:

- `super_admin` – system-wide oversight and privileged administration
- `admin` – store-scoped user and account administration
- `manager` – store-scoped operational management
- `logistics_manager` – regional supply and routing coordination
- `repair_staff` – assigned-location maintenance management
- `account_user` – registered customer with persistent profile and preferences
- `general_user` – one-time customer without persistent profile storage

The platform uses AI assistance to support, not replace, human decision-making. AI outputs are used for:

- drink recommendations for customers
- supply usage analysis and restock suggestions
- maintenance prioritization and route proposals
- store recommendation assistance

AI outputs are recommendation-oriented and explainable. Final approvals for supply and maintenance operations remain in human-controlled workflows.

---

### System Constraints

The system must operate within the following constraints:

- no centralized global server may act as the single authoritative controller for all stores
- each store must remain capable of local operation if disconnected from peers or hubs
- only regionally relevant operational data should be shared broadly
- sensitive payment and user data must be protected in transit and at rest
- access must be constrained by role, store, region, and responsibility
- synchronization conflicts must be detected and resolved safely
- imported CSV files must be validated before any operational data is applied
- maintenance and supply logic must remain configurable rather than hardcoded where possible
- the design must be maintainable as new stores, regions, and machine types are added

---

### Hardware Platform

CodePop is designed primarily as a web-based software platform accessed by customers and staff from standard browsers, with backend services logically associated with store and hub nodes.

#### Client Layer

Users access CodePop through:

- mobile web browsers for customer ordering and account use
- desktop or laptop web browsers for staff dashboards and administration
- responsive, role-aware interfaces that adapt based on user type and permissions

The client experience prioritizes:

- mobile-first design for customer flows
- fast, low-friction drink customization
- clear and minimal navigation
- large touch-friendly controls
- accessible, role-specific operational dashboards for staff

#### Store Server Layer

Each store is treated as an independent backend node in the target architecture.

A store node is responsible for:

- order processing for orders placed at that store
- local inventory ownership and updates
- local machine registry and current machine state
- store-scoped dashboards for managers and admins
- authentication and authorization enforcement for store-owned resources
- exchange of approved operational summaries with regional peers and hubs

In the target architecture, each store may have its own backend and database. In the class implementation, this behavior may be simulated within one deployed application by using store-scoped records and explicit ownership rules.

#### Supply Hub Layer

Each supply hub is a regional operational node responsible for:

- tracking hub inventory
- supporting replenishment for stores in its home region
- supporting eligible cross-region deliveries within 1000 miles
- exposing routing and stock information for logistics workflows
- serving as a higher-capacity coordination point for supply movement

#### Background Processing Layer

Some system work occurs asynchronously rather than directly inside a user request. This includes:

- notifications
- synchronization jobs
- import processing
- AI analysis tasks
- maintenance scheduling generation
- supply schedule generation

These background concerns are part of the architecture even if their exact implementation is defined later.

---

## 3. Architecture Design

### Architectural Style

CodePop follows a **Distributed Client–Server Architecture** implemented using a **regional multi-node structure**.

This architecture is chosen to satisfy several requirements at once:

- stores must operate independently
- the system must not depend on a centralized global server
- regional coordination is still necessary for logistics and maintenance
- the system must support nationwide growth without coupling every store to one central database

At a conceptual level, each store acts as both:

- a **server for its own customers and local staff**, and
- a **regional participant** in peer coordination for approved operational data

Each store node contains three logical layers:

1. **Presentation Layer** – web UI and dashboards  
2. **Application Layer** – store business logic and coordination services  
3. **Data Layer** – store-owned persistent data  

Supply hubs follow a similar model but with logistics-oriented responsibilities.

This architecture provides:

- store autonomy
- reduced blast radius during outages
- clear ownership of local data
- scalable regional coordination
- an implementation path that can be simulated in a single class deployment while still preserving correct architectural boundaries

---

### Architecture Philosophy: Real-World Target vs Class Implementation

Because this is a course project based on a provided webapp, the architecture is described at two levels:

#### Real-World Target Architecture

In a full production deployment:

- each store would run its own backend services and database
- each supply hub would run hub-owned logistics services and storage
- inter-store and store-hub communication would occur over authenticated HTTPS APIs
- synchronization would happen across node boundaries

#### Course Implementation Architecture

For the class implementation:

- the decentralized model may be simulated within a single deployed application
- store nodes and hub nodes may be represented as store-scoped and hub-scoped records inside one codebase
- ownership rules, permissions, and synchronization boundaries are still modeled explicitly
- APIs and services should be designed so the architecture could later be separated into distinct deployments if needed

This hybrid framing allows the project to remain practical while still honoring the architectural requirements.

---

### Deployment Architecture (Docker + Google Cloud)

All major backend services are containerized using Docker to support consistency across development, testing, and deployment.

The deployment model includes the following logical units:

- Django web application service
- PostgreSQL database service
- background worker service
- message broker / queue support if needed for asynchronous tasks
- optional reverse proxy and production serving layer

Each logical store node and hub node is expected to include or connect to:

- web application logic
- background processing capability
- persistent data storage
- secure network communication

Deployment options include:

- local development using containerized services
- regional infrastructure hosted on Google Cloud Platform
- hybrid deployment with some components near stores and some regionally hosted

Google Cloud Platform may be used for:

- regional compute hosting
- monitoring and logging infrastructure
- secure networking between regional nodes
- scalable background processing capacity

GCP is explicitly **not** used as a centralized global authority for all store operations.

---

### Major System Components

The major architectural components are:

- Web-Based Client Interfaces
- Store Backend Service
- Supply Hub Service
- User Management Module
- Store Management Module
- Supply Hub & Inventory Module
- Machine Maintenance Module
- Order Management Module
- Communication / Synchronization Module
- Data Import Module
- AI Services Module
- Notification Services
- Local / node-owned PostgreSQL Databases

These components communicate using authenticated interfaces and clearly defined ownership boundaries.

---

### Node Types and Ownership Model

To reduce ambiguity, the system recognizes three primary node perspectives.

#### 1. Store Node

A store node is the authoritative owner of:

- store metadata for its own location
- local inventory state
- local machine registry and current machine condition
- orders placed at that store
- local payment lifecycle metadata tied to those orders
- local operational dashboards for store roles

#### 2. Supply Hub Node

A supply hub node is the authoritative owner of:

- hub metadata
- hub inventory
- hub outbound supply availability
- hub-supported transfer and routing records

#### 3. Client/User Node

A client is not an authoritative data node. It is a user-facing interface that submits requests to the appropriate store-owned or system-approved services.

---

### Regional Coordination Model

CodePop organizes stores into regions. Each store belongs to exactly one region. Each region has one primary supply hub in the seed/test data.

The required seed regions are:

- Region A: Chicago, IL
- Region B: New Jersey / New York
- Region C: Logan, UT
- Region D: Dallas, TX
- Region E: Atlanta, GA
- Region F: Phoenix, AZ
- Region G: Boise, ID

Regional coordination rules are:

- stores may share approved operational data with other stores in the same region
- direct store-to-store supply transfers are limited to nearby stores in the same region
- the home-region hub is the preferred replenishment source
- a hub may also support stores in other regions if the destination store is within 1000 miles of the hub
- cross-region supply movement should be recommended by the system but approved by logistics personnel

This preserves decentralization while still enabling practical regional operations.

---

### Data Ownership and Synchronization Principles

The HLD adopts the following ownership principles:

#### Local by Default

The following data is local to the owning store unless a summarized or approved subset is shared:

- active orders
- payment transaction details
- immediate fulfillment state
- store-specific operational actions

#### Regionally Shared When Needed

The following operational summaries may be shared regionally:

- inventory availability summaries
- transfer eligibility and transfer status
- maintenance coordination data
- repair urgency data
- supply schedules and replenishment planning data

#### System-Wide Visibility for Privileged Roles

Some data may be visible across stores for privileged reporting and oversight roles, but that does not make it centrally owned. Visibility and ownership are separate concepts.

---

### Design Decisions

**Distributed Client–Server Architecture**  
Chosen to satisfy the no-central-server requirement while preserving user-facing responsiveness and store autonomy.

**Regional Multi-Node Coordination**  
Chosen to balance store independence with practical logistics and maintenance coordination.

**Store-Scoped Ownership**  
Chosen so that orders, inventory, and machine state have clear operational owners.

**Containerization (Docker)**  
Selected for reproducibility, portability, and team consistency.

**Relational Database (PostgreSQL)**  
Selected because orders, payments, permissions, and operational records require strong relational integrity and transactional support.

**AI-Assisted, Human-Approved Operations**  
Chosen because the requirements demand automation support but explicitly reject fully autonomous AI decision-making without human approval.

---

### Alternatives Considered

**Single Centralized Nationwide Server**  
Rejected because it conflicts with the project requirements and creates a larger single point of failure.

**Purely Isolated Stores with No Coordination Layer**  
Rejected because it prevents practical regional logistics, maintenance planning, and operational insight.

**Document-Only / NoSQL-First Data Model**  
Rejected because the project requires strong relationship management, role boundaries, and transactional workflows.

**Fully Autonomous AI Operations**  
Rejected because the scope requires AI assistance, explanations, and human oversight for operational actions.

---

## Section 4: Modules and Components (Internal Interfaces)

### 4.1 User Management Module

**Purpose:** Manage authentication, identity, role assignment, profile data, and account-scoped customer preferences.

#### Responsibilities

- user registration and login flows
- account management for registered customers
- session and authentication token handling
- role assignment and permission enforcement
- store and region scoping for staff access
- saved favorites, likes, dislikes, and preference history for account users
- complaint submission and complaint tracking
- temporary guest-order identity support for general users without creating persistent preference profiles

#### Components

- **User Service** – CRUD operations for user records and role associations
- **Authentication Service** – sign-in, sign-out, session/token lifecycle
- **Permission Service** – role, store, and region boundary enforcement
- **Preference Service** – likes, dislikes, favorites, and preference persistence
- **Complaint Service** – complaint submission, status tracking, routing
- **Guest Access Service** – supports guest order lookup and short-lived operational identity

#### Role Boundary Summary

- `super_admin` has system-wide privileged oversight
- `admin` manages users for their own store only
- `manager` uses store-level operational access only
- `logistics_manager` operates across their assigned region for supply workflows
- `repair_staff` operates for assigned store locations
- `account_user` has persistent customer profile and history
- `general_user` does not receive permanent preference/history storage

---

### 4.2 Store Management Module (Expanded)

**Purpose:** Manage store metadata, region assignment, operational status, and node-level configuration.

#### Responsibilities

- maintain store records and physical location metadata
- associate stores with exactly one region
- associate stores with a primary regional hub
- track connectivity and last-known synchronization state
- support configuration-driven addition of new stores and regions
- expose store attributes needed for recommendation, supply, and maintenance workflows

#### Components

- **Store Registry Service** – canonical store metadata, addresses, coordinates, identifiers
- **Region Service** – region records, assignments, and region-to-hub mapping
- **Store Status Service** – operational status, last sync, availability indicators
- **Store Configuration Service** – store-specific settings such as inventory thresholds and scheduling windows

#### Architectural Notes

This module is especially important because the system is no longer single-store. It creates the foundation for:

- store recommendation logic
- store-scoped permissions
- maintenance assignment
- regional supply coordination
- configuration-driven growth

---

### 4.3 Supply Hub & Inventory Module (Expanded)

**Purpose:** Manage inventory ownership, supply visibility, replenishment coordination, store-to-store transfers, hub support, and local supplier interactions.

#### Responsibilities

- track first-class inventory items at the store and hub level
- support multiple item categories including syrups, sodas, add-ins, cups, lids, ice cream, CO2, cleaning supplies, and other operationally significant consumables
- support common inventory modeling with item-type-specific attributes such as perishability or frozen storage
- manage 7 regional hubs with defined home-region assignments
- support cross-region hub deliveries within 1000 miles
- support nearby same-region store-to-store transfers
- support local supplier replenishment records
- surface low-stock alerts using configurable thresholds
- support AI-assisted usage analysis and restock recommendations
- maintain available ingredients and drink customization options

#### Components

- **Inventory Service** – on-hand quantities, thresholds, manual corrections, audit logs
- **Supply Hub Service** – hub inventory and regional support metadata
- **Transfer Service** – request, approval, reservation, in-transit, received, or canceled transfer lifecycle
- **Local Supplier Service** – supplier records, replenishment source tracking, purchase history
- **Reorder Service** – forecast-driven restock recommendations and draft schedules
- **Supply Routing Service** – routing suggestions for store and hub replenishment
- **Menu / Ingredient Service** – items available for customer ordering and customization

#### Key Design Rules

- store managers may adjust inventory for their own store, with auditing
- logistics managers coordinate supply at the regional level but do not own raw store counts as day-to-day operators
- source stock is reserved when a transfer is approved
- approved transfers may be canceled only through a controlled workflow
- local suppliers are recorded as first-class replenishment sources
- low-stock thresholds are configurable per item and per location

---

### 4.4 Machine Maintenance Module (Expanded)

**Purpose:** Track machine state, machine history, maintenance schedules, and route-aware repair planning across many stores.

#### Responsibilities

- maintain a registry of machines by store
- support multiple machines of the same type within a store
- track stable machine-type codes and machine-type-specific maintenance policies
- manage maintenance events and current machine states
- enforce seven primary status values: `normal`, `repair-start`, `repair-end`, `warning`, `error`, `out-of-order`, `schedule-service`
- track service deadlines and escalation windows
- support CSV import for maintenance updates
- support AI-assisted route and schedule recommendations
- notify assigned repair staff of urgent conditions

#### Components

- **Machine Registry Service** – machine IDs, machine types, store association, operational-from dates
- **Machine Type Policy Service** – per-type maintenance intervals and warning tolerances
- **Status Tracking Service** – current state plus historical status events
- **Repair Schedule Service** – service windows, visit constraints, assignments
- **Route Optimization Service** – prioritized route recommendations that minimize travel
- **Maintenance Alert Service** – warning, error, and overdue-service notifications

#### Key Design Rules

- each machine has a system-generated unique identifier
- maintenance rules are configurable, ideally per machine type
- a `warning` status starts a tracked service deadline countdown
- if warning exceeds its allowed window, the system escalates the machine to a higher-severity state
- repair staff may override system-generated routes and schedules when needed
- repair dashboards prioritize urgency first, with route and calendar support secondary

---

### 4.5 Order Management Module (Updated)

**Purpose:** Handle store-owned order creation, payment, scheduling, preparation timing, pickup state, cancellation, and customer-facing order lifecycle.

#### Responsibilities

- create and manage customer orders
- attach each order to exactly one selected store
- process payment at order time through an external provider
- allow refund/cancellation only before preparation begins
- support both guest checkout and account-user ordering
- support store recommendation based on location, preferred store, and pickup timing
- support same-day or near-term scheduled pickup times
- track order state from placement through pickup or expiration
- support notifications and customer-facing status updates

#### Components

- **Order Service** – order creation, state changes, ownership, and lookup
- **Payment Service** – payment provider integration and payment state updates
- **Refund Service** – cancellation validation and refund processing
- **Pickup Coordination Service** – pickup timing, ready state, and time-sensitive prep logic
- **Store Recommendation Service** – preferred store and location/time-based ranking
- **Notification Service** – order confirmations, ready alerts, expiration alerts
- **Guest Order Access Service** – guest order code lookup without full account creation

#### Order Ownership Rules

- account users may order from any store nationwide
- each order belongs to one store only
- the selected store is the authoritative owner of the order lifecycle
- payment is captured when the order is placed
- refund eligibility ends when preparation begins
- guest data is retained only for operational needs, not as a persistent preference profile

---

### 4.6 Communication / Synchronization Module (Expanded)

**Purpose:** Support decentralized store and hub coordination without turning the system into a globally centralized architecture.

#### Responsibilities

- identify regional peers and coordination relationships
- exchange approved operational summaries between nearby stores and hubs
- synchronize inventory coordination data, supply-transfer data, and maintenance coordination data
- detect synchronization conflicts and resolve them safely
- queue sync-related operations while a node is disconnected
- support eventual consistency for regionally shared operational datasets

#### Components

- **Peer Discovery Service** – identifies relevant same-region stores and eligible hubs
- **Data Sync Service** – sends and receives coordination data
- **Conflict Resolution Service** – detects conflicting changes and applies policy-driven resolution
- **Offline Queue Service** – buffers coordination operations during disconnection
- **Sync Audit Service** – logs synchronization events and reconciliation history

#### High-Level Sync Rules

- not all data is synchronized equally
- local transactional data remains local by default
- approved operational summaries are synchronized regionally
- conflicts must be detectable and auditable
- stores continue operating while disconnected and reconcile later

---

### 4.7 Data Import Module (Expanded)

**Purpose:** Provide validated bulk import of supply and maintenance operational data.

#### Responsibilities

- accept CSV uploads from authorized roles
- validate file schema before processing
- validate row contents, codes, date formats, and store references
- reject malformed rows and provide actionable feedback
- apply validated data to the appropriate store, hub, or maintenance records
- record import history for auditing and troubleshooting

#### Components

- **CSV Parser Service** – parses import files into structured rows
- **Schema Validation Service** – validates required columns and file shape
- **Value Validation Service** – validates machine codes, dates, statuses, and addresses
- **Import Processor Service** – applies accepted records to the correct entities
- **Import History Service** – stores file metadata, row counts, and errors

#### Import Design Rules

- validation occurs before operational writes are committed
- files should produce clear row-level error messages
- imports must be auditable
- maintenance CSV imports create or update maintenance events and machine status history
- supply imports feed inventory analytics and replenishment workflows

---

### 4.8 AI Services Module (Expanded)

**Purpose:** Provide explainable AI assistance across customer experience and operations.

#### Responsibilities

- generate drink recommendations for account users
- support preference-aware randomization and suggestion workflows
- analyze supply usage patterns from operational data and CSV imports
- generate replenishment suggestions and draft schedules
- optimize repair priorities and route recommendations
- generate store recommendation assistance for account users
- provide explanations for AI-generated suggestions

#### Components

- **Drink Recommendation Service** – uses order history, favorites, likes, and dislikes
- **Supply Forecasting Service** – analyzes demand and usage patterns
- **Repair Optimization Service** – prioritizes service actions and route suggestions
- **Store Recommendation Logic** – combines user preference, time, and distance signals
- **Explanation Service** – explains why AI suggested a supply or repair recommendation

#### AI Boundary Rules

- AI is assistive, not fully autonomous
- AI may propose actions, but operational approvals remain human-controlled
- recommendations should be explainable to staff users
- AI features may be implemented incrementally as long as the architecture preserves their boundaries

---

## Diagrams

The original HLD includes diagrams for:

- component interaction
- data flow
- decentralized communication
- role hierarchy and permissions

Those diagrams should be retained, but the rewritten document clarifies the assumptions they must communicate.

### 1. Component Interaction Diagram

This diagram should show:

- the main modules listed in Section 4
- where store ownership begins and ends
- how AI, import, and sync modules interact with operational modules
- which components are primarily customer-facing versus staff-facing

### 2. Data Flow Diagram (DFD)

This diagram should show:

- order data flowing into a selected store
- payment interactions with Stripe
- regional supply and maintenance coordination flows
- CSV upload entry points and validation before persistence
- which data remains local versus regionally shared

### 3. Decentralized Communication Diagram

This diagram should show:

- multiple stores in a region
- at least one regional hub
- same-region store-to-store coordination
- hub support for both home-region and eligible cross-region destinations
- no centralized global database or controller

### 4. Role-Permission Matrix Diagram

This diagram should show both **who can see what** and **who can act on what**, because visibility and authority differ across roles.

---

## 5. Data Design

### 5.1 Data Design Goals

The CodePop data design must support a multi-store distributed architecture while maintaining security, consistency, and operational clarity.

The data model must:

- support clear ownership of store, hub, and user data
- enforce role-based access boundaries
- preserve transactional integrity for orders and payments
- track inventory and machine state per location
- support region-aware coordination without requiring global real-time synchronization
- support seeded test data for stores, hubs, users, and operational records
- remain configurable as new stores, regions, and machine types are added

A relational design is used because the system depends heavily on:

- role relationships
- store and region relationships
- order/payment consistency
- inventory and maintenance history
- auditability and constraints

---

### 5.2 Key Data Entities

#### User
Represents any person using the system.

High-level attributes include:

- user identifier
- role
- account status
- contact identity
- optional home/preferred store relationship
- optional store or regional assignment for staff roles

#### Store
Represents a physical CodePop store location.

High-level attributes include:

- store identifier
- name and address
- region assignment
- coordinates/location metadata
- operational status
- configuration values and thresholds

#### Region
Represents an operational region used for coordination.

High-level attributes include:

- region code
- region name
- primary hub relationship
- geographic metadata or configuration

#### SupplyHub
Represents a regional supply hub.

High-level attributes include:

- hub identifier
- region association
- address/location
- inventory state
- support eligibility for destination stores

#### LocalSupplier
Represents a local supplier that can replenish one or more stores.

High-level attributes include:

- supplier identifier
- contact and service area metadata
- supplied item categories
- relationship to one or more stores or regions

#### Order
Represents a single customer order placed against one store.

High-level attributes include:

- order identifier
- user or guest reference
- owning store
- order state
- payment state
- requested pickup time
- timestamps

#### Ordered Drink / Drink Configuration
Represents the immutable drink configuration associated with an order.

High-level attributes include:

- drink configuration identifier
- selected ingredients and options
- size
- price snapshot
- relationship to the owning order

#### Favorite / Preference Profile
Represents persistent preference information for account users.

High-level attributes include:

- likes and dislikes
- favorites
- saved drink patterns
- recommendation support data

#### InventoryItem
Represents an inventory-tracked item at a store or hub.

High-level attributes include:

- inventory item identifier
- item category/type
- quantity
- threshold
- storage attributes
- last updated metadata

#### InventoryAdjustment / Replenishment Record
Represents a tracked change to inventory outside normal sales consumption.

Examples include:

- manual corrections
- local supplier deliveries
- transfer receipts
- transfer shipments

#### SupplyTransfer
Represents a planned or active movement of supplies.

High-level attributes include:

- source location
- destination location
- item quantities
- status lifecycle
- approval metadata
- shipment/receipt timestamps

#### MachineType
Represents a machine category and its maintenance rules.

High-level attributes include:

- stable machine type code
- display name
- service interval policy
- warning tolerance policy

#### Machine
Represents an individual machine at a store.

High-level attributes include:

- unique machine identifier
- store association
- machine type association
- operational-from date
- current status

#### MachineStatusEvent / MaintenanceRecord
Represents a status change or maintenance event for a machine.

High-level attributes include:

- machine reference
- status value
- status date
- service notes or source metadata

#### Payment
Represents a financial transaction linked to an order.

High-level attributes include:

- payment identifier
- order association
- amount
- provider status
- timestamps

#### Notification
Represents an operational or customer-facing message.

High-level attributes include:

- recipient reference
- type
- message/content metadata
- delivery state
- timestamps

#### ImportJob
Represents a CSV import event.

High-level attributes include:

- file metadata
- initiating user
- import type
- validation results
- processing results

---

### 5.3 Entity Relationships

The following high-level relationships define the system:

- **Region → Store:** One-to-Many
- **Region → SupplyHub:** One-to-One in seed data, extensible later
- **Store → InventoryItem:** One-to-Many
- **SupplyHub → InventoryItem:** One-to-Many
- **Store → Machine:** One-to-Many
- **MachineType → Machine:** One-to-Many
- **Machine → MachineStatusEvent:** One-to-Many
- **User → Order:** One-to-Many for account users
- **Store → Order:** One-to-Many
- **Order → Ordered Drink / Drink Configuration:** One-to-Many or One-to-One depending on cart model
- **Order → Payment:** One-to-One or One-to-Many depending on transaction history strategy
- **User → Notification:** One-to-Many
- **Store / Hub → SupplyTransfer:** One-to-Many as source or destination
- **LocalSupplier → Replenishment Record:** One-to-Many

These relationships are intended to give Codex and future developers a clearer starting point than the previous HLD, especially around `Store`, `Region`, and transfer/maintenance concepts.

---

### 5.4 Database Design

- **Database Type:** Relational
- **Primary Technology Choice:** PostgreSQL
- **Schema Management:** ORM-managed models with migration support
- **Indexing Strategy:** Primary keys, foreign keys, role-scoped lookups, store-scoped lookups, region-scoped lookups, time-series operational history fields
- **Configuration Strategy:** Regions, stores, thresholds, and machine-type policies should be data-driven where practical

The database design must support both:

- strong transactional workflows for local operations, and
- clear separation between local operational data and regionally shared operational summaries.

---

### 5.5 Data Access Layer

Data access is managed through an ORM-backed service layer rather than direct database access from templates or UI code.

The data access layer should:

- centralize validation and business rules
- enforce permission-aware querying
- support atomic operations for order and payment workflows
- support auditing for sensitive modifications
- keep store- and region-scoping rules consistent across modules

This approach improves maintainability and reduces the risk that generated code accidentally bypasses important permission or ownership rules.

---

### 5.6 Data Security Considerations

Data security is enforced at multiple levels:

- **Application Level:** role- and scope-based access control
- **Data Level:** encryption at rest for sensitive fields and strong password hashing
- **Transport Level:** TLS-encrypted communication
- **Operational Level:** auditable changes for admin, logistics, and repair actions
- **Ownership Level:** local data remains local unless an approved shared representation is required

Sensitive information includes:

- credentials
- payment metadata
- user profile data
- location-related customer data
- operational records tied to staff actions

---

## 6. Integration Points (External Interfaces)

### External Systems and Services

CodePop integrates with several external platforms to support payments, location intelligence, notifications, and operational workflows.

These integrations support platform functionality but do not replace CodePop’s internal ownership and business rules.

All external integrations should be treated as supporting services rather than sources of truth for core domain logic.

---

### Payment Processing System

**Provider:** Stripe

#### Purpose

- capture payment at order placement
- support refunds for valid cancellations
- support cards and digital wallets
- avoid storing raw payment instruments inside CodePop systems

#### Key Interactions

- payment intent / authorization / confirmation flow
- provider callback or status synchronization
- refund request for eligible canceled orders
- payment-state update of the owning order

#### Design Notes

- payment occurs at time of order
- refunds are permitted before preparation begins
- payment data remains tied to the order’s owning store context

---

### Geolocation Services

**Provider:** Mapbox

#### Purpose

- suggest stores based on user location and requested pickup timing
- estimate travel time
- support location-aware preparation suggestions

#### Key Interactions

- optional location permission request
- route or distance estimation
- nearest-store or feasible-store lookup

#### Design Notes

- geolocation is optional for the user
- when unavailable, the system falls back to preferred store or manual selection
- store recommendation logic must combine location with time and preference, not location alone

---

### Push Notification System

**Provider:** Firebase Cloud Messaging (FCM)

#### Purpose

- notify customers when drinks are ready
- notify staff of operational events such as low stock or urgent machine states
- support role-specific operational alerts

#### Key Interactions

- order state notifications
- low inventory alerts
- machine warning/error alerts
- optional promotional notifications where supported

---

### AI & Analytics Services

**Provider Type:** Internal Python-based AI / analytics modules

#### Used For

- drink recommendation
- usage-pattern analysis
- replenishment suggestions
- repair prioritization and route recommendation
- explainable AI outputs for staff-facing operational decisions

#### Input Sources

- order history
- account-user preferences and favorites
- inventory records
- maintenance records
- validated CSV uploads

#### Output Types

- ranked drink suggestions
- forecast summaries
- draft supply schedules
- prioritized repair queues and route suggestions
- explanation text for recommendations

---

### CSV Data Import Interface

#### Purpose

- bulk upload of supply usage or replenishment-support data
- bulk upload of maintenance and machine-status records

#### Supported High-Level Files

- supply usage data by store/date/item
- maintenance status records with store address, machine type, operational-from date, status, and status date

#### Processing Flow

1. authorized user uploads CSV  
2. system validates schema and field values  
3. invalid rows are reported clearly  
4. accepted data is applied through import services  
5. import history and audit information are recorded  
6. downstream analytics may be triggered  

---

## 7. User Interface (UI) Design Overview

### Design Principles

The CodePop interface prioritizes:

- mobile-first responsiveness for customer flows
- role-based clarity for staff dashboards
- minimal cognitive load
- accessible controls and readable status cues
- fast completion of common tasks
- consistency between dashboards where possible

Because the platform serves both customers and operations staff, the UI is intentionally split into:

- customer-facing ordering experiences
- store-level dashboards
- regional logistics and repair dashboards
- privileged administrative views

---

### Customer-Facing Interface

#### Core Screens

- home / store selection
- drink builder
- AI drink generator / suggestion view
- cart and checkout
- pickup status
- order history for account users
- favorites and preferences for account users
- guest order lookup
- payment and profile management for account users

#### Core UX Behaviors

- customers may order as guest or account user
- account users may receive store recommendations based on preference, time, and location
- customers may choose manual pickup time instead of relying only on geolocation
- preferred store should influence the ordering flow when available
- account users should see saved favorites and personalized suggestions

---

### Manager Dashboard

#### Primary Purpose

Support day-to-day operations for one store.

#### Core Views

- active and scheduled order queue
- inventory overview with low-stock signals
- revenue and payment summaries for the store
- machine status summary for the store
- cooler / pickup status if applicable

#### Allowed Actions

- review store orders and operational state
- reconcile inventory counts
- respond to operational alerts
- view store-scoped financial summaries

---

### Admin Dashboard

#### Primary Purpose

Support store-scoped account and access management.

#### Core Views

- user account list for the store
- locked/unlocked account management
- role assignment for eligible store-scoped roles
- store-level account administration and support tools

#### Allowed Actions

- update/remove/unlock users for that store
- create eligible staff accounts as permitted by the final permission model
- manage access for store-relevant accounts

---

### Logistics Manager Dashboard

#### Primary Purpose

Support regional supply coordination.

#### Core Views

- regional inventory overview
- hub inventory and capacity view
- transfer queue and transfer history
- low-stock and shortage risk panels
- local supplier replenishment history
- supply usage trends and AI suggestions
- CSV upload and import results

#### Preferred Dashboard Style

The logistics dashboard should be **operations-first**, with inventory risk and pending actions visible immediately. Map or routing visualizations are useful, but the dashboard should remain usable even as a list- and decision-oriented tool.

---

### Repair Staff Dashboard

#### Primary Purpose

Support assigned-location maintenance and travel-efficient service planning.

#### Core Views

- urgent machine queue by severity
- machine status by assigned store
- overdue-service list
- AI-recommended route/schedule view
- maintenance history view
- CSV upload and import results

#### Preferred Dashboard Style

The repair dashboard should be **urgency-first**, followed by route optimization and calendar support.

---

### Super Admin Dashboard

#### Primary Purpose

Provide cross-store and cross-region oversight.

#### Core Views

- system-wide summary metrics
- regional comparisons
- store comparisons
- user and role oversight tools
- audit and exception review
- supply and maintenance analytics across regions

This dashboard should emphasize visibility and governance rather than replacing role-specific operational screens.

---

### Navigation Flow

Navigation should remain role-aware and predictable.

The UI should use:

- mobile-friendly bottom or compact navigation for customer flows
- sidebar or dashboard navigation for staff roles
- only role-relevant menu items
- shallow navigation depth for common workflows

---

## 8. Input and Output (I/O)

### 8.1 User Inputs

#### Order Inputs

- drink customization choices
- pickup timing or preferred ready time
- preferred store or manual store selection
- geolocation permission where applicable
- order confirmation and cancellation actions

#### Account Management Inputs

- registration and login fields
- favorites and preference data
- likes and dislikes for ingredients or drink characteristics
- payment method setup through external payment provider flows

#### Operational Inputs

- inventory adjustments by authorized store roles
- transfer requests and approvals
- machine status updates
- maintenance scheduling updates
- user account management actions by admins or super admins

#### CSV Upload Inputs

- supply usage/import files
- maintenance status files
- import metadata and validation feedback handling

---

### 8.2 System Outputs

#### Customer Outputs

- order confirmations
- order-ready notifications
- cancellation or refund confirmations
- store suggestions
- drink recommendations
- guest order lookup results

#### Operational Outputs

- role-specific dashboards
- low-stock alerts
- machine warning and error alerts
- transfer recommendations and schedule proposals
- import validation results
- AI explanations for logistics and maintenance suggestions

#### Reports and Analytics

- store-level operational reports
- regional supply reports
- maintenance trend reporting
- comparison views for privileged roles

---

### 8.3 Expected Data Volumes

The HLD should assume moderate-to-large operational scale with growth over time. Exact capacity planning belongs in lower-level infrastructure planning, but the architecture must anticipate:

- many stores nationwide
- many daily orders per store
- ongoing inventory and maintenance history
- recurring import jobs and background tasks
- audit logs for sensitive actions

The design therefore favors:

- relational persistence for transactional data
- background processing for asynchronous workloads
- indexed access patterns for store-, region-, and time-based queries
- retention and archival strategies for older operational history

---

### 8.4 Scalability Considerations

The system must scale by:

- adding stores without code changes
- adding regions without code changes
- adding machine types through configuration
- supporting larger operational datasets without redesigning role boundaries
- preserving store autonomy even as the overall business grows

Scalability in CodePop is therefore not only about performance; it is also about **maintaining correct ownership and maintainable configuration as the system expands**.

---

## 9. Security and Privacy

### 9.1 Security Overview

Security is especially important because CodePop processes:

- user account information
- payment-related metadata
- customer location signals
- inventory and operational data
- maintenance records
- privileged staff actions across stores and regions

The distributed architecture increases the attack surface compared to a simple single-store application, so security must be enforced consistently across user-facing, operational, and inter-node interactions.

---

### 9.2 Authentication and Authorization

CodePop enforces secure authentication and role-based authorization using the principle of least privilege.

Authorization must account for more than just role labels. It must also consider:

- store ownership
- regional assignment
- specific location assignment for repair staff
- whether an action is view-only or write-capable

Examples:

- `admin` is store-scoped, not region-scoped
- `manager` is store-scoped operationally
- `logistics_manager` is region-scoped for supply workflows
- `repair_staff` is scoped to assigned locations
- `super_admin` has broad privileged visibility and administrative authority

---

### 9.3 Data Encryption

Sensitive data must be encrypted:

- **in transit** between browser and application services, between store and hub nodes, and between peer coordination endpoints
- **at rest** for sensitive stored information

Passwords must be strongly hashed, and payment handling must rely on external provider practices rather than storing raw instruments in CodePop.

---

### 9.4 Secure Inter-Store Communication

Any store-to-store or store-to-hub communication must use:

- authenticated channels
- encrypted transport
- trusted node identity
- validation of received data
- audit trails for synchronization-sensitive operations

This is essential because decentralization increases the importance of verifying peer identity.

---

### 9.5 Network and Infrastructure Security

Infrastructure protections should include:

- hardened deployment environments
- secure secrets handling
- rate limiting where appropriate
- network boundary protections
- monitoring and alerting for suspicious activity

A compromise of one node should not automatically compromise an entire region.

---

### 9.6 Privacy Considerations

Privacy practices include:

- collecting only necessary user data
- optional use of geolocation
- no permanent preference/history storage for general users
- limiting visibility of customer information to authorized store roles
- minimizing broad sharing of user-related data across stores unless operationally required

---

### 9.7 Logging and Auditing

The system should log and audit:

- administrative actions
- account unlock and role changes
- transfer approvals and cancellations
- maintenance status changes
- import events
- synchronization reconciliation events
- sensitive permission failures or unusual access attempts

Logging is both a security feature and a maintainability feature.

---

### 9.8 Physical and Hardware Security

Where store-hosted or location-specific infrastructure exists, physical access controls should be considered to reduce tampering risk. This includes secure handling of store-side devices and configuration access.

---

### 9.9 Security Risks and Mitigation Summary

| Risk | Impact | Mitigation |
|------|--------|------------|
| Unauthorized access | Data breach or misuse | Strong authentication + RBAC + scope filtering |
| Peer impersonation | Tampered operational data | Authenticated inter-node communication |
| Privilege escalation | Cross-store or cross-region misuse | Layered permission enforcement |
| Invalid imports | Corrupted operational records | Schema/value validation + import auditing |
| Distributed attack surface | Broader system exposure | Node hardening + monitoring + least privilege |

---

## 10. Testing Strategy

### 10.1 Testing Philosophy

Testing should validate not only feature correctness but also the architectural promises made by the system.

That means the testing strategy must verify:

- store-scoped ownership
- role boundaries
- CSV validation and safe processing
- supply and maintenance coordination behavior
- resilience during partial failures
- correctness of AI-assisted recommendations and their boundaries

---

### 10.2 Testing Levels

#### Unit Testing

Used to verify isolated services such as:

- permission logic
- order state transitions
- inventory adjustments
- CSV parsing and validation
- machine status escalation rules

#### Integration Testing

Used to verify:

- order + payment coordination
- import processing into operational records
- logistics workflows across stores and hubs
- maintenance scheduling and notification flows
- synchronization services and conflict handling

#### System Testing

Used to validate complete workflows, including:

- customer ordering and pickup
- store recommendation flow
- store manager inventory workflow
- logistics manager replenishment workflow
- repair staff maintenance workflow
- super-admin visibility and governance workflows

#### Security Testing

Used to verify:

- authentication boundaries
- cross-role access restrictions
- store and region scoping
- inter-node communication requirements
- protection of sensitive data

---

### 10.3 Test Data and Simulation

The system must include test or seed data that supports required demonstrations.

At minimum, seed data should include:

- 7 supply hubs for Regions A–G
- 20 stores in Region C
- at least 5 stores in each neighboring region within 200 miles where applicable in the project dataset
- logistics-manager coverage and supply data for hub regions
- repair-staff coverage for Region C
- machine records and maintenance states
- inventory items and thresholds
- account users and guest-order scenarios

Seed data is not an afterthought; it is part of demonstrating the architecture.

---

### 10.4 Distributed System Considerations

The testing strategy must include scenarios such as:

- store operation while disconnected
- delayed synchronization and later reconciliation
- transfer conflicts
- stale maintenance data reconciliation
- hub eligibility checks for cross-region delivery
- store-only access enforcement for admin and manager roles

---

### 10.5 Automation vs Manual Testing

Automated testing should cover repeatable service-level and role-boundary verification. Manual testing should cover:

- dashboard usability
- visual prioritization of alerts
- customer ordering flows
- edge-case import feedback

---

## 11. Risks and Mitigations

### 11.1 Architectural Risks

**Distributed Synchronization Complexity**  
Different nodes may hold competing views of operational data.  
**Mitigation:** Clearly define ownership, synchronize only approved summaries, and use auditable conflict resolution.

**Ambiguous Responsibility Boundaries**  
If role and node ownership are unclear, generated or hand-written code may expose the wrong actions.  
**Mitigation:** Define store-, region-, and role-scoped responsibilities explicitly in architecture and service design.

---

### 11.2 Operational Risks

**Supply Shortages**  
Stores may run out of key ingredients or packaging.  
**Mitigation:** Threshold alerts, store visibility, hub support, local supplier records, and AI-assisted replenishment.

**Machine Downtime**  
Critical machines may remain in degraded states too long.  
**Mitigation:** Per-machine status tracking, warning deadlines, route optimization, and priority-based repair dashboards.

**Over-Reliance on Manual Coordination**  
Regional operations may become difficult to scale.  
**Mitigation:** AI-assisted scheduling, structured transfer workflows, and role-specific dashboards.

---

### 11.3 Security Risks

**Unauthorized Access**  
Mitigated through strong authentication, RBAC, and scope enforcement.

**Inter-Node Data Interception or Tampering**  
Mitigated through encrypted and authenticated communication.

**Privilege Escalation Through Weak Role Boundaries**  
Mitigated through layered enforcement in service, view, and query boundaries.

---

### 11.4 Data Risks

**Synchronization Conflicts**  
May produce incorrect operational views if not resolved safely.  
**Mitigation:** conflict detection, audit logging, and policy-based reconciliation.

**Invalid CSV Imports**  
May corrupt inventory or maintenance records.  
**Mitigation:** schema validation, value validation, error reporting, and import history.

**Misinterpreted Ownership of Shared Data**  
Could lead to improper updates across stores or regions.  
**Mitigation:** explicit ownership table in implementation artifacts and scope-aware services.

---

### 11.5 Scalability Risks

**Rapid Expansion Across Stores and Regions**  
May strain configuration and maintainability if logic is hardcoded.  
**Mitigation:** configuration-driven stores, regions, thresholds, and machine types.

**Dashboard Complexity Creep**  
As roles expand, dashboards may become overloaded.  
**Mitigation:** keep dashboards task-oriented, role-scoped, and action-first.

---

### 11.6 Summary Table

| Risk Category | Example | Mitigation |
|--------------|---------|------------|
| Architectural | Sync ambiguity | Explicit ownership + reconciliation policy |
| Operational | Low inventory | Forecasting + hubs + local supplier support |
| Operational | Maintenance delays | Warning deadlines + prioritized repair workflows |
| Security | Unauthorized access | RBAC + scope filtering + auditing |
| Data | Invalid imports | File validation + import logging |
| Scalability | Hardcoded growth assumptions | Configuration-driven design |

---

## 12. Conclusion

This expanded High-Level Design reframes CodePop as an evolution of the provided base webapp into a multi-store, decentralized, regionally coordinated platform.

The architecture is built around several core principles:

- store autonomy
- regional coordination instead of centralized control
- clear ownership of operational data
- role-specific access and dashboards
- AI-assisted, human-approved operations
- maintainable configuration-driven growth

This document is intentionally more detailed than the earlier draft so that future implementation work, including Codex-assisted coding, can proceed with fewer ambiguous assumptions.

The next design step should be to align the Low-Level Design with this HLD by defining:

- exact state machines
- concrete model fields and relationships
- endpoint responsibilities
- background task behavior
- synchronization and conflict-resolution mechanics
- dashboard page breakdowns
- seed-data scripts and import examples
