# CodePop Final Project Report

## Team Members

- **Curt**
- **Gabriel**
- **Brock**
- **Braxton**
- **Peyton**
- **Matthew**

---

## Sprint 0: Requirements [January 26 - February 9, 2026]

### Sprint Summary

Sprint 0 focused on requirements discovery, role assignment, and completion of the rewritten requirements document. Work emphasized documenting functional, non-functional, business, and user requirements; defining use cases with diagrams; and aligning the team on scope and priorities. The sprint closed with a full-team review and final transfer/submission of the requirements document.

### Tasks & Assignments

| Task                                                                               | Owner(s)        | Status   | Work Type       |
| ---------------------------------------------------------------------------------- | --------------- | -------- | --------------- |
| Review prior project requirements and run starter project to establish baseline    | Everyone        | Complete | Docs, Prototype |
| Assign section ownership and create requirements doc outline                       | Gabriel         | Complete | Docs, Design    |
| Write introduction, MoSCoW introduction, and previous-project context              | Gabriel         | Complete | Docs            |
| Write functional, non-functional, and business requirements sections               | Braxton, Peyton | Complete | Docs            |
| Define user requirements and role-based responsibility breakdown                   | Matthew         | Complete | Docs, Design    |
| Develop MoSCoW breakdown, use case stories, and use case diagrams                  | Curt, Brock     | Complete | Docs, Design    |
| Cross-review completed requirements document and resolve inconsistencies           | Everyone        | Complete | Docs, Debug     |
| Final integration, cleanup, and transfer from draft workspace to GitHub submission | Gabriel         | Complete | Docs            |
| Configure shared GitHub repository and team access for production workflow         | Braxton         | Complete | Prototype       |

### Reflections

The largest early blocker was environment setup and dependency friction while bringing the starter project up locally. We resolved this by pairing setup checks with requirement review so progress continued while tooling issues were fixed. A structured ownership model improved accountability and throughput, but the sprint also showed we should increase cross-section collaboration in later sprints so ideas are shared earlier instead of only at review time. Direction for Sprint 1 was confirmed: preserve the strong ownership model while adding more coordinated design discussion across contributors.

---

## Sprint 1: High Level Design Documentation [February 9 - February 23, 2026]

### Sprint Summary

Sprint 1 focused on completing the High-Level Design document and establishing the overall structure of the CodePop system. During this sprint, the team broke the document into major sections covering architecture, modules and components, data design, integration points, user interface design, input and output, security, testing strategy, and risks. As sprint lead, I helped organize the document, assign work across the team, and make sure the major architectural sections stayed consistent with each other. In addition to documentation, the team also created a sample prototype to better visualize the system and support the presentation. By the end of the sprint, the High-Level Design document was completed and the team had a much clearer shared understanding of the system direction.

### Tasks & Assignments

| Task                                                             | Owner(s)         | Status   | Work Type      |
| ---------------------------------------------------------------- | ---------------- | -------- | -------------- |
| Sprint coordination, section planning, and document organization | Brock (Lead)     | Complete | Design/Docs    |
| Introduction, System Overview, and Architectural Design          | Brock            | Complete | Docs/Design    |
| Modules & Components (Internal Interfaces)                       | Gabriel, Peyton  | Complete | Docs/Design    |
| Data Design                                                      | Gabriel, Peyton  | Complete | Docs/Design    |
| Integration Points (External Interfaces)                         | Braxton, Matthew | Complete | Docs/Design    |
| User Interface Design Overview and Input/Output planning         | Braxton, Matthew | Complete | Docs/Design    |
| Security and Privacy, Testing Strategy, Risks and Mitigations    | Curt             | Complete | Docs/Design    |
| Shared Markdown collaboration file for team editing              | Curt             | Complete | Docs           |
| Sample prototype creation and review                             | Entire Team      | Complete | Prototype      |
| Presentation preparation and prototype walkthrough practice      | Entire Team      | Complete | Docs/Prototype |

### Reflections

This sprint went well because we divided the High-Level Design document into clear sections early and gave each person ownership over a specific part of the work. That made the workload more manageable and helped the team stay productive throughout the sprint. One of the biggest strengths was having a shared document and consistent communication, which made collaboration smoother and reduced version confusion once everything was consolidated.

A challenge we faced was keeping terminology, formatting, and architectural details consistent across sections, since different people were writing different parts at the same time. We also spent more time than expected cleaning up inconsistencies and aligning the final document before submission. Another smaller challenge was that some decisions, like branding and presentation details, took longer than expected because everyone had different opinions.

Overall, Sprint 1 gave us a strong architectural foundation for the rest of the project. It helped the team move from broad ideas into a more organized system design, and it also showed us the importance of early delegation, shared documentation, and regular consistency checks before moving into lower-level design and implementation.

---

## Sprint 2: Low-Level Design Documentation [February 23 - March 9, 2026]

### Sprint Summary

During this sprint, our team focused on completing the Low-Level Design (LLD) document and finalizing the detailed structure of our system. As team lead, I helped organize the document, assign sections to each team member, and ensure that all parts were completed on time and at a consistent level of detail. Each member was responsible for a specific portion of the system, including database design, security, integrations, and core features. Along with documentation, we also worked on prototyping the Price Calculator and Order functionality, which helped reinforce our design decisions. By the end of the sprint, we had a fully completed LLD document and a working prototype ready for our presentation.

### Tasks & Assignments

| Task                                                                                                                 | Owner(s)      | Status   | Work Type         |
| -------------------------------------------------------------------------------------------------------------------- | ------------- | -------- | ----------------- |
| Low-Level Design document organization & section distribution                                                        | Peyton (Lead) | Complete | Design            |
| Section 1 – Introduction, Section 2 – System Architecture, Section 7.1 – Database Schema                             | Peyton        | Complete | Docs              |
| Section 3 – User Management & Security, Section 9 – Security Considerations, Section 10 – Performance Considerations | Brock         | Complete | Docs              |
| Section 4 – Order & Payment System Design, Stripe Integration, Push Notifications (FCM), Geolocation Services        | Matthew       | Complete | Docs              |
| Section 5 – Supply Hub & Inventory Management, CSV Interface (Supply Usage)                                          | Gabe          | Complete | Docs              |
| Section 6 – Machine Maintenance & Repair Scheduling, CSV Interface (Repair Schedules)                                | Braxton       | Complete | Docs              |
| Synchronization Architecture, Conflict Resolution, Offline Handling, Data Integrity Rules, Testing Strategy          | Curt          | Complete | Docs              |
| Price Calculator & Order functionality prototypes (individual implementations)                                       | All Members   | Complete | Prototype         |
| Prototype evaluation and selection for demo                                                                          | Full Team     | Complete | Prototype         |
| Presentation preparation, speaking roles, and rehearsal                                                              | Full Team     | Complete | Docs/Presentation |

### Reflections

This sprint was very structured and productive, mainly because the work was clearly divided and everyone understood their responsibilities. As team lead, I focused on keeping the team organized, making sure each section of the LLD was completed, and helping resolve any confusion about requirements or design details. One of the biggest strengths of this sprint was how we split the document into sections, which allowed us to work in parallel and finish efficiently.

A challenge we faced was scheduling conflicts and some team members missing class time, but we handled this by meeting outside of class and staying in communication via Discord. Another key takeaway was the value of having everyone build their own prototype before choosing one, since it gave us a better understanding of different approaches.

Overall, this sprint helped solidify the technical details of our system and gave us a strong foundation to move forward into the development phase.

---

## Sprint 3: Development Phase 1 [March 9 - March 23, 2026]

### Sprint Summary

Sprint 3 focused on laying the foundational infrastructure for the CodePop backend and beginning parallel development across all major system domains. The team set up project management tooling, established Django app skeletons and core data models, and divided development responsibilities across accounts/auth, orders/payments, inventory, and machine maintenance. Spring break (March 9–13) reduced the effective sprint length, so scope was trimmed to foundational model and infrastructure work. Near the end of the sprint, the team identified that the multi-app, parallel-AI-assisted development strategy was creating integration and complexity issues, and made the decision to restructure into sub-teams for Sprint 4.

### Tasks & Assignments

| Task                                                                                         | Owner(s)                         | Status   | Work Type   |
| -------------------------------------------------------------------------------------------- | -------------------------------- | -------- | ----------- |
| Monday.com workspace setup and task tracking configuration                                   | Gabriel                          | Complete | Design/Docs |
| Django app skeleton creation (accounts, orders, inventory, maintenance, notifications, core) | Gabriel                          | Complete | Code        |
| INSTALLED_APPS configuration and root urls.py setup                                          | Gabriel                          | Complete | Code        |
| LLD diagram updates reflecting new architecture                                              | Gabriel                          | Complete | Design/Docs |
| Store, Region, and SupplyHub model creation and migrations                                   | Curt                             | Complete | Code        |
| Seed data management commands (stores, users, machines, inventory)                           | Curt                             | Complete | Code        |
| Role field and UserProfile model definition (accounts/models.py)                             | Peyton                           | Complete | Code        |
| Permission mixins and decorators scaffolded for each role                                    | Peyton                           | Complete | Code        |
| Login, register, and logout views (in progress)                                              | Peyton                           | Partial  | Code        |
| Inventory models (InventoryItem, SupplyTransfer, RestockAlert) and migrations                | Braxton                          | Complete | Code        |
| Inventory CRUD views and serializers (in progress)                                           | Braxton                          | Partial  | Code        |
| Machine, MachineStatusEvent, and RepairAssignment models and migrations                      | Brock                            | Complete | Code        |
| Machine CRUD and status update views (in progress)                                           | Brock                            | Partial  | Code        |
| New app strategy documentation and architecture redesign                                     | Brock                            | Complete | Design/Docs |
| Order, Drink, and Revenue model migration to orders app                                      | Matthew                          | Complete | Code        |
| Order and payment view migration to orders/views.py                                          | Matthew                          | Partial  | Code        |
| Stripe PaymentIntent view migration (in progress)                                            | Matthew                          | Partial  | Code        |
| Logistics dashboard prototype setup and show-and-tell preparation                            | Gabriel, Brock, Braxton, Matthew | Complete | Prototype   |

### Reflections

The sprint established all core data models and app structure across the system, with each team member owning a distinct domain. While approximately half of all tasks reached completion within the sprint window, the foundational model work was solid enough to unblock Sprint 4 development. The biggest lesson from this sprint was that splitting development across too many parallel AI-assisted workstreams caused the codebase to become fragmented and difficult to integrate — a challenge that led to a deliberate strategy shift toward smaller, higher-frequency sub-teams going into the next sprint.

---

## Sprint 4: Development Phase 2 [March 23 - April 6, 2026]

### Sprint Summary

Sprint 4 was focused on completing all development as well as preparing for testing. The team was split into groups based on their availability during each week and were given a set of tasks to complete at given times. The beginning of the spring was dedicated to repo, config, and structure changes. Once that had been completed we are able to start working on all of the features that were needing to be completed. We focused on finishing all features and development then moved on to our preparation for the testing sprint. We finished the sprint by preparing for our last show and tell.

### Tasks & Assignments

| Task                                                                  | Owner(s)                       | Status   | Work Type          |
| --------------------------------------------------------------------- | ------------------------------ | -------- | ------------------ |
| Repo, config, structure changes                                       | Gabe, Curt, and Brock          | Complete | Design/Code        |
| Orders and checkout, payment orchestration, supply hubs and transfers | Braxton and Matthew            | Complete | Code               |
| Dashboard and analitics and reporting                                 | Brock and Peyton               | Complete | Code               |
| UI Changes                                                            | Braxton, Brock, and Gabe       | Complete | Code               |
| Functionality check                                                   | Peyton and Matthew             | Complete | Code/Prototype     |
| AI integration                                                        | Matthew, Gabe, and Peyton      | Complete | Code               |
| Cloud implementation                                                  | Gabe                           | Complete | Design/Code/Debug  |
| Test Document                                                         | Curt                           | Complete | Docs               |
| Show and tell prep                                                    | Braxton, Curt, Brock, and Gabe | Complete | Presentation       |
| Full app pass through                                                 | Braxton, Brock, and Gabe       | Complete | Debug/Presentation |

### Reflections

The biggest challenge for sprint 4 was the repo, config, and structure changes that were needed at the start in order for everyone else to start working on their tasks.This took a lot more time and work than I was originally thinking. We were able to overcome that, allowing others to work on their parts. For this sprint I learned a lot about the importance of organization. I tried to organize tasks and groups as well as possible to take advantage of the time given. I found that this helped us and made us a lot more productive. I also had to be very adaptable because a lot of our tasks were delayed due to things breaking or other impediments. It was very important to be flexible to these changes and be willing to adjust the plan. Our communication was a good this sprint, but I would have still liked to improve that a little bit more. I feel that it is very helpful for each person to know how the others are doing on their tasks and to stay updated daily if possible.

---

## Sprint 5: Testing [April 6 - April 20, 2026]

### Sprint Summary

Sprint 5 focused on comprehensive testing, critical bug fixes, and documentation finalization. Work was organized into two phases: Phase 1 centered on end-to-end testing of user stories to identify bugs, while Phase 2 focused on fixing critical issues identified during testing. Testing was split among the team with each user story validated by two separate testers to ensure coverage. After bug reports were collected, critical bugs were prioritized and distributed for fixing. Documentation, including the user manual and final presentation materials, was completed in parallel. The sprint closed with final tweaks and a test run on the presentation computer to ensure delivery readiness.

### Tasks & Assignments

| Task                                                              | Owner(s)          | Status   | Work Type         |
| ----------------------------------------------------------------- | ----------------- | -------- | ----------------- |
| Testing coordination and assignment of user stories               | Curt              | Complete | Docs/Prototype    |
| End-to-end testing (Phase 1) - user stories across 6 team members | All Members       | Complete | Prototype/Debug   |
| Bug report collection and prioritization                          | Curt              | Complete | Debug/Docs        |
| Critical bug fixing (Phase 2) - distribution and execution        | All Members       | Complete | Code/Debug        |
| User manual section completion                                    | All Members       | Complete | Docs              |
| Presentation slides and speaking order                            | Curt, All Members | Complete | Docs/Presentation |
| Final presentation tweaks and computer readiness test             | All except Curt   | Complete | Presentation      |

### Reflections

Splitting testing into distinct phases (reporting vs. fixing) helped maintain focus and ensured all bugs were identified before prioritization. By requiring each user story to be tested twice by different team members, we increased coverage and confidence in the application state. Meeting deadlines was consistent across testing assignments (Friday bug reports), critical bug fixes (Sunday completion), and user manual (Wednesday). Using actionable, specific task assignments, such as testing 2 user stories per person or writing 3 manual sections, made it easier to track progress and ensure completion. The deliberate approach to testing first, then fixing, provided clarity on scope compared to ad-hoc bug fixing. A last-minute presentation computer test, though important, highlighted the value of earlier integration checks to catch environment-specific issues sooner.

---

## Final Deliverables

- **Requirements Document** — See `RequirementsDoc_Rewritten.md`
- **High-Level Design Document** — See `CodePop_High_Level_Design_Rewritten.md`
- **Low-Level Design Document** — See `CodePop_Low_Level_Design_Rewritten.md`
- **Test Design Report** — See `Test_Design_Report_Draft_1.md`
- **User Manual** — See `User_Manual.md`
- **Presentation Slides** — https://docs.google.com/presentation/d/1UolMrpBiTPXKnRVRiRGFHRh3tRkCyGz_yr7OdU-5xqY/edit
