# Brightloop — Subscription Management System

**Proposed solution · Odoo Makeathon**

Repository: https://github.com/akilcodes-7/Odoo-Makeathon

This submission describes the planned build and its acceptance criteria. It contains no application code and does not claim that the features or checks below are complete. The product brief and participant-supplied hackathon rules guide the scope; implementation choices are identified below.

## 1. Problem and intended outcome

Managing recurring contracts across separate records makes it difficult to track renewals, generate accurate invoices, reconcile payments, and understand recurring revenue. Brightloop will connect customers, subscriptions, billing, and payments in one local application with a customer self-service portal.

**End-to-end flow:** customer → product/variant and recurring plan → quotation → confirmed subscription → activation → recurring invoice → payment → updated balance and dashboard → permitted renewal or closure.

## 2. Users and responsibilities

| Role | Planned access |
| --- | --- |
| Admin | Configure products, variants, plans, taxes, discounts and quotation templates; create staff; manage operational records. |
| Staff | Manage customers, quotations and subscriptions; generate/confirm invoices; record payments; view reports. |
| Customer | View only their own subscriptions and confirmed/paid invoices; print invoices and request allowed subscription actions. |

Customer profiles may exist without a login. Signup will create and link a customer profile atomically; staff will not link an account merely because an entered email matches. Permissions will be enforced on the server for every action and record.

## 3. Chosen stack and data model

**Python 3.12 + Django 5.2 LTS + SQLite + Django templates/forms + local CSS and vanilla JavaScript.** Django provides authentication, migrations and server-side validation; SQLite supports a portable local demonstration. No cloud service or frontend build pipeline is required for core operation after dependency installation.

The data model will include users, customers, products, variants, recurring plans, taxes, discounts, quotation templates and lines, subscriptions and lines, invoices and lines, invoice tax snapshots, discount redemptions, payments, and subscription events. Foreign keys and database constraints will protect relationships and financial history.

Forms and reports will read persisted database records. A protected dashboard summary API will reuse the same reporting queries as the UI.

## 4. Build sequence

| Stage | Planned deliverable | Acceptance criterion |
| --- | --- | --- |
| Foundation | Django project, custom user model, schema/migrations, shared UI shell and demo seed command. | Fresh setup migrates successfully; repeated seeding does not duplicate demo records. |
| Authentication | Signup, login, password reset and role permissions. | Emails are unique ignoring case; passwords require 9+ characters, uppercase, lowercase and a special character; only admins create staff. |
| Configuration | Customer management; products with variant surcharges; plans with daily/weekly/monthly/yearly periods, minimum quantity, dates and lifecycle flags; taxes. | Invalid values are rejected; edits persist and appear in the UI. |
| Quotations and subscriptions | Templates with validity days; numbered contracts, dates, payment terms, lines and lifecycle actions. | Draft → Quotation → Confirmed → Active → Closed follows centralized rules; expired quotations cannot confirm. |
| Recurring billing | Billing cursor, catch-up processing, tax calculation, invoice snapshots, management command and “Run billing” action. | Repeated or concurrent processing does not create duplicate invoices or skip unbilled periods. |
| Discounts | Admin-managed fixed/percentage rules with minimum purchase/quantity, dates, usage limits and product/subscription scope. | Eligibility and capacity are enforced transactionally; old invoices retain original discounts. |
| Invoices and payments | Confirm/cancel/send/print; payment method, amount, date and note; partial/full balances. | No overpayment or duplicate payment; full settlement marks an invoice Paid. |
| Reporting and portal | Active subscriptions, collected revenue, outstanding/overdue balances, MRR, filters and customer actions. | Metrics reconcile with stored records; customers cannot access another customer's data. |
| Integration and delivery | Responsive review, permission/financial checks, performance evidence, documentation and demonstration. | Actual results and limitations are recorded; the final demo follows the full customer-to-payment flow. |

## 5. Financial and lifecycle safeguards

- Store money as integer paise; use Decimal arithmetic and explicit rounding, never floating-point money. INR is the initial currency.
- Keep subscription and invoice transitions in one lifecycle service. Invoice flow is Draft → Confirmed → Paid; cancellation is allowed only under defined unpaid-invoice rules.
- Store `next_invoice_date`; enforce a unique `(subscription, period_start)` constraint. Invoice creation, discount reservation and cursor advancement will share one transaction per period. Bounded catch-up leaves remaining periods due for the next run.
- Use calendar-aware month/year boundaries. Snapshot customer billing details, prices, taxes and discount allocations on invoices so later edits cannot alter history.
- Guard discount usage increments in the invoice transaction. Project choice: one eligible rule per invoice, selecting the greatest saving with a deterministic tie-break; no stacking.
- Record payments atomically with a unique request key; validate the current balance before insertion. Calculate overdue from confirmed unpaid balance and due date, rather than storing an overdue status.
- Enforce plan flags for auto-close, close, pause and renewal. Project choices: pause from the next unpaid period; renewal creates a new draft for staff confirmation; prorate a shortened final period.
- Define collected revenue as payments received. Show MRR before discounts/tax, normalized as daily × 365/12, weekly × 52/12, monthly unchanged, yearly ÷ 12; label it as an estimate.
- Generate billing through a management command and document optional local scheduling. Print uses a print-friendly page. Offline email uses console/file output and is labeled as local output, not delivered mail.

## 6. Hackathon requirement coverage

### Must have

| Supplied requirement | Planned approach |
| --- | --- |
| Dynamic data, not static JSON | SQLite-backed forms, lists, invoices and dashboard API; seed data only initializes the demo. |
| Clean, responsive, consistent UI | Shared layouts, colors, form controls, financial tables and mobile navigation. |
| Robust input validation | Django forms, service validation and database constraints; useful inline errors. |
| Intuitive navigation and spacing | Role-aware menus, clear headings/actions, breadcrumbs and consistent spacing. |
| Team Git participation | Each contributor uses their own identity, feature branches, meaningful commits and PR reviews. |

### Nice to have

| Supplied guideline | Planned approach |
| --- | --- |
| Backend APIs, data modeling and local database | Django ORM, SQLite and authenticated dashboard summary endpoint. |
| Understand AI/code snippets | Contributors explain and adapt generated logic, recording relevant decisions in PRs. |
| Offline/local operation | Local assets, database and email fallback; document installation and actual-email network needs. |
| Use technology only when it adds value | Keep the stack small; add dependencies only for a demonstrated requirement. |

## 7. UI and performance

Use a light workspace, plum navigation, teal accents, readable money columns and reusable components. Mobile navigation will become a drawer; forms will stack and wide tables will scroll within their containers. Support keyboard focus, visible errors and reduced-motion preferences. Restrained 120–200 ms transitions will enhance buttons, drawers and page entry.

Seed approximately 5,000 subscriptions **with related invoices and payments**. Use pagination, relevant indexes, joined queries and database aggregates. Measure representative pages against the under-two-second target and record dataset size, machine context and timings. Server response measurements and browser observations will be reported separately; the target remains unverified until measured.

## 8. Team schedule and documentation

Times are planned for **31 October 2026, IST**, not records of completed work. Teammates join only after 13:00.

| Time | Owner | Focus |
| --- | --- | --- |
| 09:00–09:40 | Lead | Foundation, schema and common UI. |
| 09:40–10:30 | Lead | Authentication, roles and customer linking. |
| 10:30–11:30 | Lead | Product, variant, plan and tax management. |
| 11:30–13:00 | Lead | Subscriptions, billing spine, shared service contracts and handoff. |
| 13:00–16:15 | Teammate 1 | Discounts and quotation templates. |
| 13:00–16:15 | Teammate 2 | Payments, balances, invoice send/print. |
| 13:00–16:15 | Teammate 3 | Dashboard, MRR and customer portal. |
| 13:00–17:00 | Lead | Integration, permissions, validation, reviews and performance checkpoint around 14:30. |
| 16:15–17:00 | Everyone | Final integration, evidence, demo rehearsal and code freeze. |
| 17:00–17:30 | Submission owner | Frozen-build video, upload and link submission. |

The lead owns shared models/services and layout assets; teammates own their feature modules. Each contributor will maintain timestamped progress, checks and blockers. A shared handoff will identify working features, pending tasks and integration dependencies; a consolidated log will record decisions and verified milestones. Actual progress will never be backdated to match this schedule.

Participant-supplied administrative deadlines: repository URL at **09:00**, evaluator access by **10:00**, coding ends **17:00**, video link by **17:30**. Portal permissions and completion must be verified separately. The repository owner handles evaluator access; Akilan is the provisional portal submitter. This plan does not claim any submission or invitation is complete.

## 9. Final validation and demonstration

1. Verify fresh setup and seeded admin/staff/customer access.
2. Create a customer, select a variant and recurring plan, issue a quotation, confirm and activate it.
3. Run billing twice to demonstrate duplicate prevention; inspect discount/tax snapshots and totals.
4. Record partial and final payments; demonstrate outstanding balance, Paid status and invoice printing.
5. Show dashboard totals/MRR and the customer's restricted portal with a permitted renewal or close action.
6. Present validation failures, permission checks, responsive screenshots, measured performance and real Git contributions.
7. Record the final code commit, known limitations and video link; verify evaluator access and saved submission separately.

Initial scope excludes payment gateways, refunds/credit notes, multi-currency, mid-cycle upgrades and advanced analytics. These are project deferrals, separate from the organizer's nice-to-have guidelines. Required functionality and accurate evidence take priority over visual extras.

**Sources:** participant-provided `Subscription_Management_System.pdf`; participant-pasted rules from the [hackathon portal](https://hackathon.odoo.com/hackathon/details/79054); participant-supplied schedule and deadlines. Authenticated portal requirements have not been independently verified.
