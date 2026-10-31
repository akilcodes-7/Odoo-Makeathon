# Requirements and traceability

Status at initial publication: every build requirement below is **planned, not implemented**. Replace a status only when evidence exists. Evidence should name a check and link a commit/PR or saved result; a tick alone is insufficient.

## Source distinction

The PDF supplies product requirements. The website rules below were pasted by the participant after the portal required login. Decisions in the build specification fill gaps in the brief and are explicitly project assumptions, not organizer rules.

## Website must-have requirements

| ID | Requirement | Planned mechanism | Evidence required | Status |
| --- | --- | --- | --- | --- |
| W1 | Real-time or dynamic data; avoid static JSON beyond prototyping | Database-backed HTML views, mutation forms, and dashboard API; edits survive restart | Create/edit record, reload, restart; show updated UI | Planned |
| W2 | Responsive clean UI, consistent color/layout | Shared tokens/components and mobile navigation; locally served assets | Screenshots at 390 px, 768 px, and 1440 px | Planned |
| W3 | Robust input validation | Forms plus service checks plus DB constraints; object permissions | Positive and negative cases in focused tests | Planned |
| W4 | Intuitive navigation and proper spacing | Role-aware sidebar, page headings, breadcrumbs, visible primary action | Complete demo without navigation dead ends | Planned |
| W5 | Proper Git use by more than one member | Separate identities, branches, small commits, PR review | Real contribution history and PR URLs | Planned |

Dynamic data does not mandate WebSockets. Do not add a simulated live indicator or fabricated changing figures.

## Website nice-to-have requirements

| ID | Requirement | Plan |
| --- | --- | --- |
| N1 | Backend APIs, data models, local database | Django service layer/ORM/SQLite; authenticated dashboard JSON endpoint; REST API expansion optional |
| N2 | Understand and adapt AI/code snippets | Every contributor explains their logic in their PR and records important generated-code adaptations |
| N3 | Offline/local operation | Local app/database/assets/seed/email fallback; document initial installation and actual-email network needs |
| N4 | Trendy technology only where useful | Django templates and vanilla JS; extra dependencies need a named benefit |

## Product scope from the PDF and participant clarifications

| ID | Requirement | Owner/cards | Acceptance evidence | Status |
| --- | --- | --- | --- | --- |
| P1 | Unique email, 9+ character upper/lower/special password, email reset | Lead S1 | Duplicate-email case variants rejected; reset token works; delivery mode disclosed | Planned |
| P2 | Admin/staff/customer roles; admin-only staff creation | Lead S1 | Direct endpoint and foreign-record permission checks | Planned |
| P3 | Customers linked to login accounts; staff customer management | Lead S1/S3 | Signup creates profile; internal customers can exist without login | Planned |
| P4 | Product name/type/sales price/cost/notes; variant surcharge | Lead S2 | Variant adds 560.00 in example without changing base product | Planned |
| P5 | Plan price, daily/weekly/monthly/yearly period, minimum quantity, dates, flags | Lead S2/S3 | Form validation and lifecycle actions honor flags | Planned |
| P6 | Quotation templates with plan/lines/validity days | Teammate 1 T1B | Template copies records; expired quote cannot confirm | Planned |
| P7 | Numbered subscription, customer/plan/dates/terms/lines/taxes/amounts | Lead S3 | Complete saved subscription and line totals | Planned |
| P8 | Draft → Quotation → Confirmed → Active → Closed | Lead S3 | Allowed transitions work; skipped/reversed transitions rejected | Planned |
| P9 | Automatic recurring invoices with taxes; no duplicates or missed periods | Lead S4 | Repeat/catch-up/concurrent-run checks; scheduler command configured | Planned |
| P10 | Invoice confirm/cancel/send/print; Draft → Confirmed → Paid | Lead S4 + teammate 2 T2B | Snapshot print/email; cancellation and payment rules | Planned |
| P11 | Admin-only fixed/% discounts; minimums, dates, limits, product/subscription scope | Teammate 1 T1A | Boundary/usage/eligibility checks and invoice snapshot | Planned |
| P12 | Payments: method/amount/date/note, invoice allocation, outstanding/overdue | Teammate 2 T2A | Partial/full payment, no overpayment or duplicate submission | Planned |
| P13 | Active subscriptions, revenue, payments, overdue, filters and summary | Teammate 3 T3A | Known seeded totals and filter reconciliation | Planned |
| P14 | Thousands of subscriptions, pages under 2 seconds | Lead S5/I1 + teammate 3 | Recorded 5,000-record measurements and environment | Planned |
| P15 | Customer portal; own subscriptions/invoices and permitted close/renew | Teammate 3 T3B + lead S3 | Own-record success, foreign-record 404, flags honored | Planned |
| U1 | MRR normalized across all four periods | Teammate 3 T3A | Defined formula, seeded known values | Planned |
| U2 | Attractive UI with restrained animation | Lead S0/I1; all owners use components | Responsive and reduced-motion review | Planned |
| U3 | Full hackathon documentation | Every contributor | Honest logs, handoff, decisions, check evidence, demo instructions | In progress |

U1–U3 are explicit participant additions. The PDF asks for revenue but does not define an MRR formula. Taxes, pause/renew behavior, discount stacking, partial terms, currency, and report definitions follow the documented project assumptions.

## Participant-supplied hard deadlines

[Deadline tracker](DEADLINES.md) is authoritative for the updated schedule: repository URL at 09:00, evaluator access by 10:00, coding stops at 17:00, video URL by 17:30 IST on 2026-10-31. Portal permissions, evaluator-handle instructions, and actual completion need verification; these have not been independently confirmed through the authenticated portal. These administrative requirements do not replace feature acceptance checks.

## Product extras after required work

Payment gateway integration, retrying failed charges, automatic reminders, PDF file export beyond browser print, multi-currency, refunds/credit notes, usage billing, tax compounding, customer upgrades mid-cycle, and additional analytics are outside the initial build. These are project deferrals, not the website's official nice-to-have list.

