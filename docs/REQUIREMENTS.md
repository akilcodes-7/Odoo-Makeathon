# Requirements and traceability

Status at initial publication: every build requirement below is **planned, not implemented**. Replace a status only when evidence exists. Evidence should name a check and link a commit/PR or saved result; a tick alone is insufficient.

## Source distinction

The PDF supplies product requirements. The website rules below were pasted by the participant after the portal required login. Decisions in the build specification fill gaps in the brief and are explicitly project assumptions, not organizer rules.

## Website must-have requirements

| ID | Requirement | Mechanism | Status and evidence |
| --- | --- | --- | --- |
| W1 | Real-time or dynamic data; avoid static JSON beyond prototyping | Database-backed HTML views, mutation forms, and dashboard API | Implemented; auth/catalog/payment persistence tests and 5,000-row DB fixture pass. Restart test exists for catalog pricing. See integration suite. |
| W2 | Responsive clean UI, consistent color/layout | Shared tokens/components and mobile navigation; locally served assets | Responsive CSS/drawer and reduced-motion support implemented; only 890×921 browser view inspected. 390/768/1440 screenshots remain pending. |
| W3 | Robust input validation | Forms, services, DB constraints and object permissions | Implemented and tested across auth, catalog, lifecycle, billing, payment, delivery and portal suites. |
| W4 | Intuitive navigation and proper spacing | Role-aware sidebar, headings, visible actions | Implemented; browser navigation and local dashboard rendered. Full demo rehearsal remains pending. |
| W5 | Proper Git use by more than one member | Separate identities, branches, small commits, PR review | Incomplete: integrated code commit `0b436d9` is on local `codex/remaining-core` using the configured repo author. No PR/review or separate human teammate commits are recorded yet. |

Dynamic data does not mandate WebSockets. Do not add a simulated live indicator or fabricated changing figures.

## Website nice-to-have requirements

| ID | Requirement | Plan |
| --- | --- | --- |
| N1 | Backend APIs, data models, local database | Django service layer/ORM/SQLite; authenticated dashboard JSON endpoint; REST API expansion optional |
| N2 | Understand and adapt AI/code snippets | Every contributor explains their logic in their PR and records important generated-code adaptations |
| N3 | Offline/local operation | Local app/database/assets/seed/email fallback; document initial installation and actual-email network needs |
| N4 | Trendy technology only where useful | Django templates and vanilla JS; extra dependencies need a named benefit |

## Product scope from the PDF and participant clarifications

| ID | Requirement | Owner/cards | Status and evidence |
| --- | --- | --- | --- |
| P1 | Unique email, 9+ character upper/lower/special password, email reset | Lead S1 | Implemented; `tests.test_auth` (7) covers case-insensitive uniqueness, exact password rule, one-use reset token and POST/CSRF logout. Email backend defaults to console. |
| P2 | Admin/staff/customer roles; admin-only staff creation | Lead S1 | Implemented; team/customer/payment/template/portal access checks cover role-gated endpoints. |
| P3 | Customers linked to login accounts; staff customer management | Lead S1/S3 | Implemented; signup creates the customer atomically; internal creation remains unlinked; own profile form is scoped. |
| P4 | Product name/type/sales price/cost/notes; variant surcharge | Lead S2 | Implemented; `tests.test_catalog` (10) covers paise conversion, variant validity/effective price and archive. The separate ₹560 example was not captured. |
| P5 | Plan price, daily/weekly/monthly/yearly period, minimum quantity, dates, flags | Lead S2/S3 | Implemented; catalog/lifecycle/portal tests cover eligibility, minimum and action flags. |
| P6 | Quotation templates with plan/lines/validity days | Teammate 1 T1B | Implemented; `tests.test_templates` (6) covers admin create, staff use, plan/primary validation, copied price independence, validity and access. |
| P7 | Numbered subscription, customer/plan/dates/terms/lines/taxes/amounts | Lead S3 | Implemented; `tests.test_subscription_views` and billing snapshots cover persisted drafts, validation and line/tax snapshots. |
| P8 | Draft → Quotation → Confirmed → Active → Closed | Lead S3 | Implemented through `core.services.lifecycle`; tests cover normal path, invalid skips, expired quote, pause/resume/close/renew edges and events. |
| P9 | Automatic recurring invoices with taxes; no duplicates or missed periods | Lead S4 | Billing command and POST action implemented; repeat, catch-up, rollback, proration and concurrent duplicate tests pass. No OS/background scheduler is configured. |
| P10 | Invoice confirm/cancel/send/print; Draft → Confirmed → Paid | Lead S4 + teammate 2 T2B | Implemented; snapshot send/print and mail-failure tests pass. Delivery uses console email by default; no external delivery receipt verified. |
| P11 | Admin-only fixed/% discounts; minimums, dates, limits, product/subscription scope | Teammate 1 T1A | Implemented; 12 discount tests plus competing-invoice max-usage concurrency test pass. |
| P12 | Payments: method/amount/date/note, invoice allocation, outstanding/overdue | Teammate 2 T2A | Implemented; partial/full, replay, validation, overdue and distinct concurrent overpay tests pass. No gateway integration. |
| P13 | Active subscriptions, revenue, payments, overdue, filters and summary | Teammate 3 T3A | Implemented; 4 reporting tests and 5,000-row backend measurements pass. |
| P14 | Thousands of subscriptions, pages under 2 seconds | Lead S5/I1 + teammate 3 | Backend checks passed on 5,000 subscriptions + 5,000 invoices/lines + 2,500 payments; exact environment/timings in `DEMO_AND_CHECKS.md`. Browser rendering and concurrent-load timings remain unmeasured. |
| P15 | Customer portal; own subscriptions/invoices and permitted close/renew | Teammate 3 T3B + lead S3 | Implemented; 9 portal tests cover scoped IDs, allowed/blocked actions, invoices, print and profile route. |
| U1 | MRR normalized across all four periods | Teammate 3 T3A | Implemented using Decimal normalization and integer paise; hand-calculated/empty/customer-scope reporting tests pass. |
| U2 | Attractive UI with restrained animation | Lead S0/I1; all owners use components | Core UI and reduced motion implemented; 890×921 browser view inspected. Exact 390/768/1440 and contrast/a11y review remains pending. |
| U3 | Full hackathon documentation | Every contributor | In progress; actual test/benchmark evidence updated. Final commits/push/PR evidence, screenshots and portal/video records are pending. |

U1–U3 are explicit participant additions. The PDF asks for revenue but does not define an MRR formula. Taxes, pause/renew behavior, discount stacking, partial terms, currency, and report definitions follow the documented project assumptions.

## Participant-supplied hard deadlines

[Deadline tracker](DEADLINES.md) is authoritative for the updated schedule: repository URL at 09:00, evaluator access by 10:00, coding stops at 17:00, video URL by 17:30 IST on 2026-10-31. Portal permissions, evaluator-handle instructions, and actual completion need verification; these have not been independently confirmed through the authenticated portal. These administrative requirements do not replace feature acceptance checks.

## Product extras after required work

Payment gateway integration, retrying failed charges, automatic reminders, PDF file export beyond browser print, multi-currency, refunds/credit notes, usage billing, tax compounding, customer upgrades mid-cycle, and additional analytics are outside the initial build. These are project deferrals, not the website's official nice-to-have list.

