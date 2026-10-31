# Bounded implementation task cards

Use one card per model request. A small model should not need the entire conversation. Read AGENTS.md, docs/DEADLINES.md, the assigned card, referenced specification sections, and the existing files in scope. Cards are ordered by dependency, not merely by UI appearance. Coding ends at 17:00 IST; the 17:30 video deadline does not extend implementation time.

## Copyable request for any card

```text
Implement card <ID> from docs/TASK_CARDS.md.
Read AGENTS.md and the specification sections referenced by that card.
Stay within its file ownership and established service contracts.
Complete its acceptance checks; report actual outcomes, not assumptions.
Update your contributor log and handoff status with an actual IST timestamp.
Return behavior implemented, changed files, checks, limitations, and next dependency.
Do not rebuild the architecture or implement unrelated cards.
```

The contributor or assigned model chooses no alternative framework. If an essential dependency is missing, complete its prerequisite or report the exact blocker rather than inventing an incompatible substitute.

## S0 — Repository scaffold, complete initial schema, UI shell

**Current implementation status:** S0 files, models, migrations, local seed command and shell are implemented. Django check, fresh migration, repeat seed, placeholder route smoke checks, role-menu smoke checks, static JavaScript check and desktop visual inspection passed. An actual narrow mobile-browser screenshot has not been captured; check mobile CSS on a narrow viewport before marking S0 acceptance fully verified.

- **Owner/window:** Lead, 09:00–09:40 target. **Dependencies:** None.
- **Read:** specification §§1–3, 8, 12, 14.
- **Files:** requirements.txt, manage.py, config/, app configs/__init__, accounts/models.py/managers.py, core/models/, migrations, namespace stubs, shared templates/static, seed_demo skeleton, .env.example, README.
- **Build order:** pin Django; create custom User before migrations; create every domain model including redemption/tax snapshots/events; wire app/URL namespaces; migrate fresh DB; build shared shell; seed roles; update run instructions.
- Include database constraints and indexes, not just form validation. Implement the shared dataclasses and temporary discount hook. Register support admin pages without bypassing lifecycle services or granting business staff Django-admin access.
- Mount feature namespaces with a clearly labeled empty-state page if their routes are incomplete. Do not display fabricated dashboard metrics.
- Build tokens, sidebar, header, table, field errors, badges, buttons, responsive drawer, print base, and reduced-motion CSS. Add a static preview/demo view only if it is explicitly labeled and not confused with real app data.
- **Acceptance:** fresh virtualenv install; `manage.py check`; migrations apply to a new local database; every required model discovered; repeated seed does not duplicate users; page renders at mobile/desktop sizes with local assets.
- **Handoff:** exact pinned dependencies, verified commands, model names/fields, known stubs, screenshot of shell if actually rendered.

## S1 — Authentication, role enforcement, customer identity

- **Owner/window:** Lead, 09:40–10:30 target. **Dependencies:** S0.
- **Read:** §§3–4, 11.
- **Files:** accounts/, customer forms/views in subscriptions/ or a lead-owned customers module mounted in its existing namespace, auth templates, tests/test_auth.py, seed_demo.
- Build email signup/login/logout, password reset, role decorators/mixins, centralized scoped selectors, customer creation/profile editing, admin-only staff creation.
- Signup transaction creates a CUSTOMER user and linked Customer. Existing internal customers are not automatically claimed. Customer edits cannot alter role, ownership, prices, or accounting fields.
- Password validator: length>=9, upper/lower/special; exact behavior reused at reset and staff creation. Normalize emails; return useful duplicate validation even under a DB race.
- Configure console email by default and optional SMTP env settings. Add reset templates and generic request acknowledgement. Seed two customer logins to exercise isolation.
- **Checks:** `Alice@Example.com` and `alice@example.com` cannot become separate users; 8 characters fails, valid 9 characters passes; missing upper/lower/special fails; tampered role ignored; staff-creation POST denied to staff/customer; foreign customer records denied; reset token valid then invalid after use; logout POST requires CSRF.
- **Handoff:** exact demo login instructions; permitted role matrix; verified email mode and actual delivery limitation.

## S2 — Products, variants, plans, taxes

- **Owner/window:** Lead, 10:30–11:30 target. **Dependencies:** S0/S1.
- **Read:** §§3, 5, 11–12.
- **Files:** catalog/, templates/catalog/, catalog CSS, tests/test_catalog.py; lead coordinates model fixes.
- Build persisted list/create/edit/detail/archive screens with pagination, search, consistent forms, help text, and no hard-coded product JSON.
- Include product cost/notes/type, variant attribute/value/surcharge, plan primary product/unit price/frequency/minimum/availability/all four flags, and tax percentage conversion.
- Admin writes only; staff read/select; customers get only eligible catalog information via their portal, never product cost.
- **Checks:** ₹560 surcharge preserved as 56000 paise; wrong-product variant rejected; invalid dates/negative effective prices/zero quantities rejected; referenced records archived safely; malicious staff POST rejected; edits survive restart.
- **Handoff:** screens and known constraints; seed product/plan IDs should be looked up by stable identifiers, not guessed numeric IDs.

## S3 — Subscription creation and centralized lifecycle

- **Owner/window:** Lead, starts 11:30, prerequisite for S4. **Dependencies:** S1/S2.
- **Read:** §§3–8, 11.
- **Files:** subscriptions/, core/services/{dates,money,pricing,lifecycle}.py, templates/subscriptions/, tests/test_lifecycle.py.
- Build customer selection, line formsets, primary product/quantity/variant validation, payment terms, dates, quote expiry, totals preview, number generation, details/stepper/events.
- Implement legal transitions and lifecycle services including pause/resume/close/renew. UI buttons must call these services, not mutate fields directly.
- Freeze confirmed contract prices/fields. Define the pause boundary, terminal proration, and renewal draft behavior exactly as in the spec. Use stub billing integration until S4, then replace it before marking closure/pause fully complete.
- Manual quotes work before teammate 1's template picker. Expose a narrow template-copy hook without duplicating it.
- **Checks:** standard lifecycle; illegal skip/backward change; expired quote; missing primary line; min quantity; future activation; plan flags; confirmed line edit rejected; month-end and leap-year dates; renewal ownership/overlap/duplicate request; events recorded.
- **Handoff:** service signatures and examples; which lifecycle actions remain blocked until billing integration.

## S4 — Recurring billing spine and invoice states

- **Owner/window:** Lead, through ~12:45 target. **Dependencies:** S3.
- **Read:** §§7–10, especially transaction ordering.
- **Files:** core/services/billing.py, lifecycle invoice helpers, run_billing command, internal billing action, minimal invoice detail/list namespace coordinated with finance owner, tests/test_billing.py and test_concurrency.py.
- Before teammates branch, place finance stubs/minimal templates in their final intended paths; teammate 2 then owns extensions. Do not leave two competing invoice implementations.
- Implement all snapshots, unique period constraint, atomic write/cursor advance, bounded catch-up, early/expired/paused filtering, additive tax math, backend rounding, zero-discount hook, confirm/cancel states.
- Add the Run billing POST and management command with as-of support. Keep a command report of created/existing/error/backlog counts. Only the local demo/test command accepts explicit simulated dates; normal UI uses today.
- **Checks:** repeating same run; two concurrent same-period attempts; transaction rollback; several missed periods; catch-up cap preserves backlog; month/year anchor; terminal partial period; no billing after expiry/closed; paused gap; taxes and rounding; historical invoice unchanged by product/customer/tax edits; cancellation cannot cause rebilling; paid/partially paid cancellation denied once payments integrate.
- **Handoff:** stable stub signature and dataclasses for teammate 1; invoice fields/states for teammate 2; no unbounded webpage billing loop.

## S5 — Morning checkpoint, scale fixture, handoff

- **Owner/window:** Lead, 12:45–13:00 target. **Dependencies:** available S0–S4 work.
- **Read:** §§13–15.
- **Files:** seed_scale, benchmark_pages, docs/TEAM_HANDOFF.md, logs, README; tests only for fixture invariants if needed.
- Create about 5,000 subscriptions with related invoices/lines/payments. Make fixtures clearly local demo records and seed safely on repeat.
- Measure available list/detail routes; record missing routes honestly. Prepare exact clone/setup/seed commands and the pushed base commit. Populate the four owner rows and identify integration contracts.
- **Acceptance:** teammate can clone a known commit and start locally; pending requirements clearly visible; early benchmark evidence or explicit blocker is recorded. No fake performance pass.

## T1A — Discounts

- **Owner/window:** Teammate 1 after 13:00. **Dependencies:** S4 contracts/schema.
- **Read:** §§3, 7–9, 12, 14. **Files:** offers/services/discounts.py, offers discount forms/views/urls/templates/static, tests/test_discounts.py, docs/logs/teammate-1.md.
- Replace the empty hook and usage-reservation stub; no billing signature changes without lead coordination.
- Build admin CRUD with kinds/scopes/minimums/dates/usage caps. Eligibility uses period start, integer line bases, deterministic best rule, no stacking. Allocate fixed amounts exactly. Guard usage increment inside the caller's invoice transaction and create immutable redemption snapshots.
- **Checks:** fixed/percentage; product scope; both minimums; start/end boundaries; expired/exhausted/inactive; max uses=1 with competing invoices; billing repeat; zero saving; rounding/allocation exactness; changing rule does not change old invoices; staff/customer CRUD denied.
- **PR evidence:** screenshot and example invoice reconciliation. Merge a minimal working discount path early, then expand cases in a second PR.

## T1B — Quotation templates

- **Owner:** Teammate 1. **Dependencies:** S3, final template models. **Read:** §§3, 5–6.
- **Files:** offers/services/templates.py, template forms/views/urls/templates, tests/test_templates.py.
- Admin creates template with selected plan, lines, quantities/prices/taxes, validity days. Staff select template during draft creation through an agreed integration hook. Copy data into independent subscription rows; no active references for prices.
- **Checks:** plan/primary line/quantity validation; calculated quote expiry; edits to source template don't alter quote; expired confirmation blocked by lead lifecycle service; staff can use but not edit templates.

## T2A — Payments and balance calculations

- **Owner/window:** Teammate 2 after 13:00. **Dependencies:** S4 schema/lifecycle. **Read:** §§3, 6, 10.
- **Files:** finance/services/payments.py, finance forms/views/urls/templates/static, tests/test_payments.py, docs/logs/teammate-2.md.
- Build payment recording/list/history and shared balance selector. Validate all payment fields, invoice state and remaining balance. Use UUID submission idempotency and atomic balance recheck. Ask lifecycle helper to mark PAID; do not write status independently.
- **Checks:** partial/full payment, overdue before/after, due today, zero/negative/overpaid amounts, future date, same-key replay/conflict, concurrent distinct payments exceeding balance, cancelled/draft invoice rejection, permission denial.
- **PR evidence:** one invoice before and after partial/full payment with reconciled balances.

## T2B — Invoice send/print and finance polish

- **Owner:** Teammate 2. **Dependencies:** S4/T2A. **Read:** §§10–12.
- **Files:** finance/services/delivery.py, invoice detail/send/print templates/views, tests/test_delivery.py.
- Add confirmed/paid send action, local console/file email message and environment SMTP path, immutable snapshot print view, payment history, current balance, state-aware buttons.
- **Checks:** send prohibited to customer/foreign record; invalid/missing address produces clear error; email failure not reported as delivery; preview print without navigation; totals match saved records; invoice old address remains after customer edits; no raw cost price shown.
- **PR evidence:** print preview and disclosure of actual email mode, not a fabricated “delivered” claim.

## T3A — Dashboard, MRR, filters

- **Owner/window:** Teammate 3 after 13:00. **Dependencies:** S4 schema; payment selector may initially be implemented against specified model. **Read:** §§10–13.
- **Files:** insights/, templates/insights/, feature CSS, tests/test_reporting.py, docs/logs/teammate-3.md.
- Implement current active/outstanding/overdue/MRR cards, selected-range cash collections, filters, overdue table, one small local chart or accessible trend table. Provide JSON summary API using same selectors.
- Avoid join-multiplication bugs and N+1 fetching; use SQL sums/counts/subqueries or separate aggregates. Bound all displayed tables and retain filters across pagination.
- **Checks:** hand-calculated seed totals; partial payments; empty sets; each plan's MRR; paused/expired/closed excluded; temporary discount exclusion label; range versus current-snapshot semantics; role scoping; 5,000-record benchmark.
- **PR evidence:** dashboard screenshot and known-number reconciliation, plus measured performance if available.

## T3B — Customer portal

- **Owner:** Teammate 3. **Dependencies:** S1/S3/S4; T2 for print reuse. **Read:** §§4, 6, 10–12.
- **Files:** portal/, templates/portal/, tests/test_portal.py.
- Build own summary, subscription list/details, permitted close/pause/resume/renew, confirmed/paid invoice list/details/print, own profile entry point.
- Apply scope filtering before object retrieval; call lead lifecycle helpers; never expose internal action routes, product cost, other accounts, or global metrics.
- **Checks:** each allowed own-record action; forbidden flags; changing IDs across customers; posted customer ID ignored; invoice print isolation; renewal shows draft request; responsive navigation and empty states.

## I1 — Integration, verification, documentation, demo

- **Owner/window:** Lead after 13:00, all contributors support. **Dependencies:** incoming PRs.
- Review shared contracts and require each owner to include checks. Merge small changes, run appropriate focused suites, then complete the full workflow.
- Around 14:30 run the integrated 5,000-record benchmark; inspect list/report queries and add only justified fixes. Check core pages at 390/768/1440 widths; keyboard use and reduced motion; offline local assets.
- Freeze lower-priority polish around 16:15; finish required defects, README, current status, evidence, demo rehearsal and repository access verification. Finish code merges/pushes and record final commit before the hard 17:00 cutoff.
- **Acceptance:** docs/DEMO_AND_CHECKS.md has actual results or explicit failures; logs and requirements status agree with the implementation; fresh clone setup tested; known limitations visible; each contributor's genuine Git activity linked.
- **Final handoff:** commit/PR references, exact run commands/demo accounts, evidence locations, email/scheduler status, incomplete requirements, and next steps.

## V1 — Frozen-build recording and video submission

- **Owner/window:** Akilan with participant's help, recording preparation before 17:00 and final upload/submission by 17:30 IST. **Dependencies:** I1 frozen code commit.
- **Read:** docs/DEADLINES.md and docs/DEMO_AND_CHECKS.md.
- Confirm official video length/platform/access rules in the portal; the five-minute script is a suggested rehearsal format.
- Record the actual working flow and disclose incomplete features. After 17:00 do not modify code, merge fixes, or push further code.
- Upload by internal target 17:25, verify playback and intended viewer access, and have the verified portal submitter save the video URL.
- **Acceptance:** video URL plays for intended viewers; the portal shows the saved link; actual submission time/receipt and frozen commit are recorded. A file on the developer's machine or a URL copied to chat is not a completed portal submission.

