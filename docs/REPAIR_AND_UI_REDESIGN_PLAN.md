# Brightloop — Functional Repairs and UI Redesign Plan

Prepared: 31 October 2026, 11:57 IST.

Status: **Partial implementation in local `Main` at `0e5595b`; A07 renewal eligibility and controls have been corrected and regression checks added. Other repairs and the UI acceptance gates remain incomplete.**

Audited baseline: local `dev`, commit `32f797da48d0173f0a78db40cc6aed498e66e3ae`.

Team handoff update, 31 October 2026, 12:02 IST: **`dev` (lowercase) is the single shared integration and handoff branch**, explicitly confirmed by the user. The repository default stays unchanged. Clone with `git clone --branch dev https://github.com/akilcodes-7/Odoo-Makeathon.git` and use this document as the main repair/UI checklist.

## 1. Objective and governing references

Repair the ten reproduced functional defects, complete the remaining acceptance gaps, and redesign the existing application using the visual and interaction principles in the supplied [Apple Design skill](https://github.com/emilkowalski/skills/blob/apple-skill/skills/apple-design/SKILL.md).

Repository references:

- [Contributor instructions](../AGENTS.md)
- [Hard deadlines](DEADLINES.md)
- [Functional audit and reproductions](AUDIT_2026-10-31.md)
- [Task cards](TASK_CARDS.md)
- [Implementation specification](IMPLEMENTATION_PLAN.md)
- [Current handoff](TEAM_HANDOFF.md)

The repository specification continues to control business rules, permissions, financial calculations and service contracts. The requested UI redesign revises the presentation direction in specification §12; record the resulting component and interaction decisions there during implementation.

## 2. Scope and constraints

- Keep Python 3.12, Django 5.2, SQLite, Django templates, local CSS and vanilla JavaScript.
- Preserve integer paise storage, Decimal calculations, immutable invoice snapshots and lifecycle-owned transitions.
- Preserve POST/CSRF protection, server-side permissions and customer ownership checks throughout the redesign.
- Keep fonts, icons, scripts and styles local. Use system fonts and local SVG icons.
- Scope the redesign to existing workflows and missing written acceptance criteria.
- Preserve existing service contracts. Coordinate any necessary shared changes through the lead.
- Preserve the current uncommitted audit documentation and any newer contributor work.
- Stop implementation, code merges and code pushes at **17:00 IST on 31 October 2026**.
- Deployment and portal submission are outside this plan.

## 3. Baseline and acceptance policy

The audit discovered 96 tests: 93 passed and 3 concurrency cases skipped in the default in-memory database. The separate on-disk concurrency run passed all 3. These tests missed the ten reproduced defects, so passing the current suite alone is insufficient for completion.

For each repair:

1. Add a regression check that reproduces the actual failure through the relevant endpoint or service.
2. Implement the smallest correction that satisfies the written rule.
3. Run its focused regression and relevant adjacent checks.
4. Record actual results and remaining limitations.
5. Integrate a coherent increment before continuing dependent work.

Use isolated temporary databases for destructive or concurrent checks. Keep generated databases, environments and caches out of Git.

## 4. Phase 1 — Restore financial and contract integrity

Estimated effort: 60–90 minutes, with independent catalog work performed in parallel where possible.

| ID | Defect and owned area | Planned correction | Acceptance gate |
| --- | --- | --- | --- |
| A01 | Stale draft save undoes confirmation; `subscriptions/views.py` | Enter the writer transaction before reloading the subscription, checking DRAFT, binding forms and saving terms/lines. Reject stale writes to a contract that has progressed. Avoid saving stale lifecycle fields through a draft form. | Interleave real confirmation with an edit attempt. The edit is rejected; confirmed status, prices, dates and event history remain consistent. Add an on-disk concurrent check where practical. |
| A02 | Tax edit reduces the rate by 100×; `catalog/forms.py` | Remove double conversion between stored basis points and displayed percentages. Make the initial-value contract explicit. | A stored 1800-bps tax displays 18.00%; an unchanged endpoint submission preserves 1800 bps. Cover boundary values and two-decimal percentages. |
| A03 | Failed forms corrupt money/rate values and can crash; `catalog/forms.py`, `offers/forms.py` | Preserve submitted strings during bound-field rendering. Convert stored integer initial values exactly once. Render invalid text safely with adjacent validation errors. | Product, plan, variant and discount forms retain the original values after unrelated errors. Correcting the unrelated field saves the intended amount. Nonnumeric inputs return validation rather than HTTP 500. |
| A04 | Product creation ignores POST data; `catalog/views.py` | Bind the product form to submitted data, save valid admin input and retain invalid input. | A valid admin POST creates exactly one product and redirects. Verify persisted paise values and continued staff/customer denial. |

Do not mark these repaired based only on direct form unit tests. Exercise successful endpoints, failed-form rendering and resubmission.

## 5. Phase 2 — Repair lifecycle, validation and billing edges

Estimated effort: 60–90 minutes; some work can overlap Phase 1 under disjoint ownership.

| ID | Defect and owned area | Planned correction | Acceptance gate |
| --- | --- | --- | --- |
| A05 | Malformed plan IDs cause HTTP 500; subscription creation/editing | Use validated model selections before dependent queries. Handle malformed GET selections with a controlled response. | Invalid text, missing IDs, nonexistent IDs and unavailable plans produce useful errors. Valid selections still populate and save lines. |
| A06 | Confirmation accepts archived selections; lifecycle validation | Recheck current plan/product/variant eligibility at confirmation. Keep the saved agreement of an already confirmed contract intact. | Archive a selection after quotation and attempt confirmation: it is rejected without a partial transition. Existing confirmed contracts remain usable. |
| A07 | Final-period renewal and control visibility | **Implemented locally:** shared eligibility derives the final service period from the billing anchor and is used by lifecycle and both detail pages. Renewal start dates before the current term/purchased period ends are rejected. Regression checks cover the final-period boundary, future confirmed contracts and staff/customer action visibility. | Focused and full suites pass. Full A07 acceptance still needs explicit after-expiry/early-close, duplicate/concurrent-request and abandoned-successor checks. |
| A08 | Paused auto-close contracts never finalize; billing/lifecycle | Include expired paused contracts in finalization while distinguishing an intentional pause cursor from outstanding billable work. | The contract closes after expiry without charging the paused interval or generating zero-day invoices. Outstanding earlier debt remains payable. |
| A09 | One inconsistent cursor aborts billing; billing batch | Catch per-subscription cursor validation failures, report the affected contract and continue independent work. Preserve failed cursors. | A malformed contract returns an actionable error while a valid contract in the same batch bills successfully. A repeat does not duplicate successful invoices. |
| A10 | Simulated future billing uses inconsistent dates; lifecycle/billing | Use the captured billing `as_of` throughout a trusted activation path inside the lifecycle module. Preserve public service contracts and the ordinary UI's current-date behavior. Reconcile error/backlog reporting. | Future `--as-of` activates and bills a due confirmed contract; ordinary activation still rejects a future start. Failed activation is visible in the report. |

## 6. UI direction

Apply the reference's principles of immediate feedback, clear hierarchy, predictable spatial relationships, restrained depth, considered typography and accessible motion. Adapt them to a financial workspace.

### Visual system

- Use a quiet neutral canvas, white content surfaces, plum selected navigation and teal primary actions.
- Use system typography with deliberate size, weight and line height; align money with tabular numerals.
- Standardize spacing, control heights, corner radii, borders and shadows through shared tokens.
- Restrict subtle translucency to navigation, toolbars and dialogs; keep financial tables and form content opaque.
- Provide solid fallbacks for unsupported blur and for reduced-transparency or increased-contrast preferences.
- Keep touch targets at least 44×44 px and focus indicators visible.

### Interaction system

- Provide immediate pressed feedback; commit actions through the existing form/POST behavior.
- Keep drawer/dialog transitions short and reversible. Animate compositor-friendly properties.
- Preserve input and validation context; show pending, successful and failed states clearly.
- Confirm consequential pause/close/cancel actions with specific consequences and labels.
- Respect reduced motion, keyboard operation, focus restoration and text scaling.
- Use CSS and existing JavaScript for the required interactions. Gesture physics and animation packages are outside the required redesign.

### Design checkpoint

Establish the shared tokens and three representative page layouts first: dashboard, subscription form and invoice detail. Review their visual hierarchy and interaction states before propagating the components across all screens. Use actual local demo records and explicit empty/error states.

## 7. Phase 3 — Implement shared UI and page layouts

Estimated effort: 90–120 minutes, overlapping independent backend repairs where ownership permits.

| Area | Planned layout and behavior | Principal files |
| --- | --- | --- |
| Shared shell | Refined sidebar, compact topbar, breadcrumbs, consistent page actions, accessible mobile drawer and consistent message/confirmation components. | `templates/base.html`, `templates/components/`, `static/css/{tokens,base,components}.css`, `static/js/app.js` |
| Dashboard | Clear metric hierarchy; distinct current-snapshot and date-range sections; compact filters; readable collections and overdue tables. Preserve metric definitions. | `templates/insights/`, `static/css/insights.css` |
| Catalog | Consistent list headers, search, pagination, pricing/availability groups, inline help and errors, useful archive feedback. | `templates/catalog/`, `static/css/catalog.css` |
| Discounts/templates | Group eligibility, value, scope, dates and usage; clarify template selection and saved-copy behavior. | `templates/offers/`, `static/css/offers.css` |
| Subscriptions | Status stepper; grouped customer and term fields; clearer line editing; server-calculated line/tax totals preview; event history and explicit lifecycle consequences. Label previews appropriately; historical invoices continue to use saved snapshots. | `templates/subscriptions/`, lead-owned view context where required |
| Invoices/payments | Prominent status, total and remaining balance; aligned financial rows; payment history; state-aware actions; standalone print layout. | `templates/finance/` |
| Customer portal | Clear account summary, own-record navigation, truthful renewal state, bounded related invoices and useful empty states. | `portal/views.py`, `templates/portal/` |
| Auth/customer/team forms | Compact, consistent forms with readable instructions, adjacent errors and clear navigation. | `templates/registration/`, `templates/core/` |

Main forms and navigation must remain usable without JavaScript. The redesign must not expose internal costs, global metrics or unauthorized actions to customers.

## 8. Phase 4 — Complete written acceptance gaps

- Add bounded/paginated confirmed-and-paid invoices to portal subscription detail; filter before rendering and show the correct empty state.
- Display a successor's saved lifecycle status, including active and abandoned/closed successors.
- Complete the subscription stepper, totals/tax preview and internal pause/close disclosure.
- Expand `seed_demo` to two customer logins and representative products, variants, four plan periods, tax, contract states, invoice states and payments.
- Build fixture records through domain services where feasible. Keep repeat seeding safe and never reset existing passwords silently.
- Preserve clear disclosure of console email, manual billing scheduling and other genuine limitations.

## 9. Proposed ownership and integration

These assignments are for future execution; creating this plan does not spawn agents.

| Owner | Bounded assignment | Ownership boundary |
| --- | --- | --- |
| Lead | A01/A05–A10; shared UI; service contracts; integration | Sole editor of lifecycle, billing, subscription views, shared CSS/JS, settings/root routes and any necessary schema changes. |
| Catalog/input agent | A02–A04 and their regressions | Catalog forms/views and offer money/rate fields; coordinate test-file ownership before starting. |
| Page UI/portal agent | Page templates, feature CSS, portal presentation and bounded invoice list | Works after shared component contracts exist; does not edit common CSS/JS or lead-owned services/views. |
| Verification/fixture agent | Isolated workflow review and `seed_demo` completion | Initially read-only verification; owns seed files and explicitly assigned regression files only. |

All owners start from the current `dev` and integrate completed increments back into `dev`; it is the sole shared handoff target. Use isolated task branches/worktrees where required by repository workflow. Otherwise use disjoint files and serialize shared edits. Assign each test file to one editor at a time. Review and integrate small completed increments frequently. Delegated agent work does not count as separate human Git participation.

## 10. Verification gates

### Functional regression gate

- All A01–A10 regression scenarios pass.
- Full test suite passes; run concurrency cases separately against an on-disk temporary database.
- Django system check, migration drift check, JavaScript syntax and diff whitespace checks pass.
- Confirm historical invoice identity, amounts, taxes and discounts remain unchanged by current-record edits.
- Recheck authorization, CSRF, customer isolation, duplicate billing, discount usage limits, payment replay and concurrent overpayment prevention.

### End-to-end workflow gate

Exercise actual endpoints and browser interactions for:

1. Admin creates a product, variant, plan, tax, discount and quote template.
2. Staff creates a customer and subscription draft, including a failed validation/resubmission.
3. Staff issues, confirms and activates a quote.
4. Billing creates the due invoice; repeat billing creates no duplicate.
5. Staff confirms the invoice and records partial then full payment.
6. Print uses saved data; send reports the actual configured email backend outcome.
7. Customer sees only their own records and performs permitted lifecycle/renewal actions.
8. Dashboard figures reconcile with persisted invoices/payments and the written MRR definition.

### Visual/accessibility gate

- Inspect representative forms, lists, detail pages and navigation at 390, 768 and 1440 px.
- Check keyboard navigation, skip link, visible focus, drawer/dialog trapping and focus restoration.
- Check text zoom, reduced motion, reduced transparency and increased contrast where supported.
- Verify actual text/control contrast and that tables scroll inside their containers without full-page horizontal overflow.
- Save evidence for success, empty, validation error, pending and forbidden-action states.
- Record any browser-control limitation explicitly; do not claim a viewport check without evidence.

### Performance gate

Run the specified dataset of 5,000 subscriptions with related invoice lines and payments. Measure authenticated dashboard, subscriptions, invoices, customer detail and portal routes after relevant query changes. Record cold and ten warm samples, query counts, environment and actual row counts. Also observe representative browser navigation separately; server measurements alone do not establish browser performance.

## 11. Schedule and fallback priorities

The following are estimates, not completion claims. Reassess after the first repair increment.

| Target window, 31 October 2026 IST | Planned work |
| --- | --- |
| 12:00–12:15 | Refresh remote state, preserve local audit work, establish branch/file ownership and regression cases. |
| 12:15–13:30 | Repair A01–A04; progress independent lifecycle fixes and define shared UI tokens/components. |
| 13:30–14:45 | Finish A05–A10 and integrate; apply representative UI layouts and portal/seed corrections. |
| 14:45–16:15 | Complete page rollout, endpoint/browser workflow checks and performance/accessibility evidence. |
| 16:15–16:40 | Resolve remaining required defects; finish focused regression and full integration checks. |
| 16:40–16:55 | Final review, documentation, authorized `dev` integration/push and remote read-back. |
| 17:00 | Hard stop for implementation, code fixes, code merges and code pushes. |

If time tightens, prioritize:

1. Confirmed-contract integrity, financial input correctness and product creation.
2. Remaining lifecycle/billing defects and server validation.
3. Usable core workflows, ownership/security and required acceptance evidence.
4. Consistent shared UI across existing pages.
5. Decorative translucency and additional motion polish.

Any incomplete item remains visible in the handoff. Simplify visual treatment before reducing functional verification.

## 12. Deliverables and definition of done

- Ten defect repairs with actual regression evidence.
- Consistent redesigned shared components and existing feature screens.
- Required portal, subscription and seed acceptance gaps resolved or explicitly recorded.
- Actual responsive, accessibility, integration and performance results.
- Accurate README, task status, requirement coverage, contributor log, consolidated log and handoff.
- Coherent repair and UI commits, integrated into `dev` and read-verified when authorized and authenticated; preserve `main` and the remote default branch.
- No blanket completion claim until the failing audit scenarios and required acceptance gates pass.

Implementation begins only in a subsequent execution request. This document records the plan; it does not represent completed repairs, UI changes or new verification results.
