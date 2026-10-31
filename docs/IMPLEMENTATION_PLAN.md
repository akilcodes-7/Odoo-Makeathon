# Brightloop implementation specification

This is the executable build specification. Follow the named decisions instead of rediscovering architecture on each task. Planned behavior is not evidence of implementation. Sections are numbered so task cards can point to the minimum necessary context.

## 1. Scope, timeline, and immediate repository submission

Follow the participant's timing in IST: solo 9:00–13:00, team available only after 13:00, coding ends at 17:00. Video-link submission ends at 17:30. If actual work starts later, record actual times and remaining work; do not imply the planned morning already happened. The participant's [hard deadlines and owners](DEADLINES.md) supersede relative setup estimates.

### Immediate repository and evaluator-access priority

1. The repository-link deadline is **09:00 IST**, not a new 20-minute window. At the 09:43 checkpoint that time has passed; first verify whether Akilan already submitted a repository URL. Do not assume the external submission is missing just because this workspace has no Git remote.
2. Put this plan, README, requirements, task cards, handoff, and logs in the intended repository. Current documents honestly say the app is not implemented. Initialize Git if absent and use the actual contributor's identity; do not invent an identity or remote URL.
3. Push to the identified user-owned repository when authorized and verify the files render. If submission is still missing, the person with portal submission access should submit immediately if the portal permits it. Verify the submission permission; leader-only problem editing does not establish submission permissions.
4. **By 10:00 IST**, the repository owner handles collaborator access for evaluator Harshil Patel. Participant instruction: add `hapt-odoo` and `hackathon-odoo` unless the portal says otherwise. Record actual invitation versus accepted-access status and organizer-required permission level.
5. If the portal demands running code at initial submission, include an honestly labeled runnable scaffold; the supplied rules do not establish whether a documentation-only initial submission is accepted. Inspect actual instructions rather than making that claim.

### Morning and afternoon

| Planned time | Owner | Deliverable |
| --- | --- | --- |
| 09:00–09:40 | Lead | S0: project, all initial models/migrations, shell/components, seed skeleton, first push |
| 09:40–10:30 | Lead | S1: authentication, roles, customer linking, reset flow |
| 10:30–11:30 | Lead | S2: custom catalog/plan/tax management screens using shared components |
| 11:30–12:45 | Lead | S3/S4: subscription lifecycle and billing engine with discount stub |
| 12:45–13:00 | Lead | S5: handoff, scale seed and early performance baseline if integrated routes exist |
| 13:00–16:15 | Teammate 1 | T1A/T1B: discounts and quotation templates |
| 13:00–16:15 | Teammate 2 | T2A/T2B: payments, balances, send/print |
| 13:00–16:15 | Teammate 3 | T3A/T3B: dashboard/MRR and portal |
| 13:00–17:00 | Lead | I1: reviews, lifecycle gaps, validation, integration, scale evidence; checkpoint around 14:30 |
| 16:15–17:00 | Everyone | Focus on integration/demo/docs; unfinished requirements take priority over visual extras |
| 16:55–17:00 | Lead + everyone | Final code push and commit recorded; stop coding at 17:00 |
| 17:00–17:15 | Akilan + participant | Record demonstration of frozen build; no code changes |
| 17:15–17:25 | Akilan + participant | Upload video, check playback/access, submit link by internal 17:25 target |
| 17:30 | Akilan provisionally | Hard video-link submission deadline; confirm portal submitter |

The exact estimates are targets. If behind, reduce animation polish and secondary charts, and process fewer catch-up periods per run. Never advance past an unbilled period to appear current. Record unfinished work explicitly.

## 2. Fixed stack and repository structure

Python 3.12, Django 5.2 LTS (resolve and pin an available current 5.2 security patch at setup), SQLite, Django templates/forms/session auth, local CSS and vanilla JS. Use standard-library Decimal/calendar/date helpers. No separate frontend build or REST framework needed. Freeze the actual installed versions in requirements.txt; do not invent a patch version in advance.

```text
manage.py
requirements.txt
.env.example                         # documented keys, placeholders only
config/{settings,urls,wsgi,asgi}.py
accounts/{models,managers,forms,views,urls,validators,permissions,admin}.py
accounts/migrations/0001_initial.py  # custom User before first migrate
core/models/                        # shared domain models, lead owned
  {__init__,catalog,customers,discounts,subscriptions,invoices,payments}.py
core/migrations/
core/admin.py                       # role-protected support interface
core/services/{money,dates,pricing,lifecycle,billing}.py
core/selectors.py                   # reusable permission-scoped queries
core/management/commands/{seed_demo,seed_scale,run_billing,benchmark_pages}.py
catalog/{forms,views,urls}.py
subscriptions/{forms,views,urls}.py
offers/{forms,views,urls}.py
offers/services/{discounts,templates}.py
finance/{forms,views,urls}.py
finance/services/{payments,delivery}.py
insights/{views,urls,selectors}.py
portal/{views,urls}.py
templates/base.html
templates/components/{sidebar,field,table_pagination,status_badge,empty_state,messages}.html
templates/{registration,catalog,subscriptions,offers,finance,insights,portal}/
static/css/{tokens,base,components,pages}.css
static/js/app.js
static/icons/                        # local SVGs, no remote font/icon fetch
tests/{test_auth,test_catalog,test_lifecycle,test_billing,test_discounts,
       test_payments,test_portal,test_reporting,test_concurrency}.py
docs/                               # plan, progress, handoff, evidence
```

Each package used as a Django app has AppConfig and __init__.py. Export domain models from core/models/__init__.py so Django discovers them. Cross-app imports flow from feature apps into core; core imports the narrow offers discount hook only at the service boundary, never from models. Avoid signals for financial side effects.

Set AUTH_USER_MODEL before the first migration. Use environment variables for SECRET_KEY, DEBUG, ALLOWED_HOSTS, email settings, and demo passwords. Document that `.env` is not auto-loaded by Django; either explicitly load it with one pinned lightweight dependency or use shell exports. Default decision: shell exports, standard library os.environ, no dotenv dependency. Local settings are development-only; do not claim deployment readiness.

SQLite: set a reasonable timeout and `OPTIONS: {"transaction_mode": "IMMEDIATE", "timeout": 20}` for short, explicit atomic write transactions. Leave ATOMIC_REQUESTS off. This serializes writers; select_for_update is not a SQLite row-lock guarantee. Keep rendering, emails, and slow loops outside transactions. See section 9 for lock retries.

## 3. Data model: common conventions

- BigAutoField IDs; created_at/updated_at where mutable; created_by for financial records and significant actions.
- Store currency amounts as BigIntegerField with `_paise` suffix; nonnegative constraints except variant extra price, which may be signed but cannot produce a negative final unit price.
- Quantities are positive integers (software seats/items). Fractional quantities are outside this build.
- Currency is INR for the whole application. Display `₹1,234.50`, never raw paise.
- Rates use integer basis points: 10000 = 100%, 1800 = 18%. Forms accept percent to at most two decimal places and convert exactly.
- Dates use DateField for billing; timezone-aware timestamps for events; TIME_ZONE Asia/Kolkata, USE_TZ True. Capture one `as_of` date per billing run.
- Use PROTECT for financial/customer/catalog references. Archive referenced products/plans/taxes/discounts with is_active=False; do not cascade-delete billing history.
- Derived values such as outstanding balance and overdue are not mutable statuses. Stored invoice totals are immutable financial snapshots after creation.

### Model definitions (all created in S0)

| Model | Required fields and constraints |
| --- | --- |
| User (accounts) | AbstractUser-derived, username removed; email as login; name fields; role ADMIN/STAFF/CUSTOMER default CUSTOMER; normal auth flags; email normalized trim/lower in manager/forms/save; `UniqueConstraint(Lower('email'))`; custom manager; USERNAME_FIELD=email. is_staff is Django-admin access, not the business STAFF role; only ADMIN accounts get that flag. |
| Customer | nullable OneToOne user PROTECT; display_name, billing_email, phone optional, billing_address, is_active. Signup creates user+customer atomically. Staff may create a customer without login; never attach a user merely because a typed email matches. |
| Product | name, type SOFTWARE/SERVICE/ADDON, sales_price_paise, cost_price_paise, notes, is_active. |
| ProductVariant | product FK, attribute_name (e.g. Brand), attribute_value (e.g. Odoo), extra_price_paise, is_active; unique(product, attribute_name, attribute_value). One selectable variant per line for MVP. |
| Tax | name, rate_bps 0–10000, is_active; price-exclusive, additive taxes. |
| Plan | name, primary_product FK, price_paise, period DAILY/WEEKLY/MONTHLY/YEARLY, min_quantity >=1, available_from, available_until nullable, auto_close, closable, pausable, renewable, is_active. Availability means eligible subscription start dates, not a global expiry of existing contracts. |
| Discount | name, kind FIXED/PERCENT, amount_paise nullable, percent_bps nullable, scope PRODUCTS/SUBSCRIPTION, products M2M, min_purchase_paise default0, min_quantity default0, starts_on, ends_on nullable, max_uses nullable, used_count default0, is_active; exactly one value for selected kind; used_count>=0; max_uses positive when set. |
| QuoteTemplate | name, plan FK, validity_days >=1, notes, is_active. |
| QuoteTemplateLine | template FK, product FK, variant nullable, is_primary, quantity, unit_price_paise, taxes M2M, position. Exactly one primary line enforced in formset/service; at most one via conditional unique constraint. |
| Subscription | number unique, customer FK, plan FK, renewed_from nullable self OneToOne (one direct successor), source_template nullable FK, status DRAFT/QUOTATION/CONFIRMED/ACTIVE/CLOSED, start_date, expiry_date inclusive, payment_terms_days>=0, quote_expires_on nullable, billing_anchor_date, billing_period_index>=0, next_invoice_date nullable, billing_period snapshot, auto_close_snapshot, closable_snapshot, pausable_snapshot, renewable_snapshot, min_quantity_snapshot, is_paused bool, pause_effective_on nullable, closed_on nullable, closure_reason, currency='INR'. Copy flags/minimum on confirmation so later plan edits do not alter the agreed contract. |
| SubscriptionLine | subscription FK, product FK, variant nullable, is_primary, description, quantity, unit_price_paise, taxes M2M, position; immutable after confirmation; exactly one primary line as above. |
| Invoice | number unique, subscription FK, period_start, period_end exclusive, invoice_date, due_date, status DRAFT/CONFIRMED/PAID/CANCELLED, customer_name/email/address snapshots, currency, subtotal_paise, discount_paise, tax_paise, total_paise, terms_days_snapshot, created_by nullable (scheduled runs), sent_at nullable; unique(subscription, period_start); positive period length and nonnegative totals. |
| InvoiceLine | invoice FK, source_line FK PROTECT, product_name/variant_description snapshots, quantity, unit_price_paise, period_numerator_days, period_denominator_days, subtotal_paise, discount_paise, taxable_paise, tax_paise, total_paise, position. No recalculation from live product records. |
| InvoiceLineTax | invoice_line FK, source_tax FK PROTECT, tax_name, rate_bps, amount_paise snapshot. |
| DiscountRedemption | invoice OneToOne, discount FK PROTECT, discount_name, kind, value_paise/value_bps snapshot, total_discount_paise; one selected discount per invoice. Per-line allocation is stored on InvoiceLine. |
| Payment | invoice FK PROTECT, method BANK/CARD/CASH/OTHER, amount_paise>0, paid_on, note, created_by, idempotency_key UUID unique; immutable records in initial build. |
| SubscriptionEvent | subscription FK, actor nullable, action, from_status/to_status, occurred_at, note; records pause/resume/renew/close and status transitions. |

Generate human numbers using the database PK inside the creation transaction, e.g. SUB-000001/INV-000001. A temporary random unique identifier may be used until the PK exists; never use count()+1 or max()+1. Numbers need uniqueness, not legally compliant gapless sequencing.

Indexes: Subscription(status,next_invoice_date), (customer,status), (expiry_date); Invoice(status,due_date), (subscription,period_start), (invoice_date); Payment(invoice,paid_on), (paid_on); existing FK indexes; unique lower-email index. Add indexes only where relevant query measurements justify them; do not duplicate the unique constraint index.

## 4. Access control and authentication

| Action | Admin | Staff | Customer |
| --- | --- | --- | --- |
| Create staff/change roles | Yes | No | No |
| Change products/plans/taxes/discounts/templates | Yes | No | No |
| Read catalog and use templates | Yes | Yes | Eligible active plans/catalog only |
| Manage customer profiles | Yes | Yes | Own display/contact fields only; no user linkage/role edits |
| Create/edit draft subscriptions, quote, confirm, activate | Yes | Yes | No internal transition endpoints |
| Pause/resume/close/renew subscriptions | Yes, honoring contract flags | Yes, honoring flags | Own subscriptions, honoring flags |
| Run billing, confirm/cancel invoices, record payments | Yes | Yes | No |
| Send/print invoice | Yes | Yes | Own confirmed/paid invoices: view/print; no internal send action |
| Dashboard | Company | Company | Own-account summary only |

Server-side object lookup for customer-owned resources must filter `customer__user=request.user` before get_object_or_404. Foreign record IDs return 404. Staff/admin actions use explicit decorators/mixins and service actor checks. Hiding links is supplementary. For JSON use 401/403 consistently; HTML unauthenticated access redirects to login.

Signup: email, display name, password and confirmation; ignore submitted role or staff flags. Validate 9+ characters, at least one uppercase, one lowercase, one non-alphanumeric non-whitespace special character; no digit requirement. Reject all-whitespace and password mismatch. Apply the same validator to reset/admin creation. Hash with Django APIs. Do not rely on framework default validators for this exact rule.

Normalize email before authentication and saving; enforce case-insensitive uniqueness at DB level and convert races into form errors. Limit to the demo's documented email syntax; international email canonicalization beyond trim/lower is not required.

Use Django PasswordResetView/ConfirmView and token generator with customized forms/templates. Generic success response for unknown emails. Configure console output locally, SMTP from environment optionally. README/demo must say console output is a local fallback; it does not actually deliver mail. Customer accounts created later for an internal customer require an explicit admin-verified linking/invitation flow; no automatic claiming by email.

## 5. Product pricing, contracts, and validation

Explicit price decision: a plan's price is the recurring **unit price of its primary product**, not an additional fee charged on top of every line. On initial quote population:

- Primary line unit price = plan.price_paise + selected variant.extra_price_paise.
- Add-on line unit price = product.sales_price_paise + selected variant.extra_price_paise.
- Exactly one primary line, matching plan.primary_product; primary quantity >= plan.min_quantity.
- Staff can negotiate a nonnegative draft unit price; accepted subscription lines retain that price. Taxes are selected from active configured taxes and snapshotted into invoices at billing time.
- Product cost is internal only; never display it in the portal.

Validate variant belongs to chosen product; positive integer quantities; input currency at most two decimals; positive dates/terms; expiry>=start; available_from<=available_until; start within plan availability; active plan/product selection; selected discount products when product scope. Catch DB IntegrityError as a useful form error.

Freeze subscription lines, dates, period, and plan flag/minimum snapshots at confirmation. Existing contracts are unaffected by later catalog/plan edits. For an MVP, reject active contract edits; renew into a new draft to change terms. Tax rules remain live until an invoice is created, as requested by the admin-defined tax behavior; old invoices retain snapshots.

## 6. Lifecycle and quotation templates

Single module `core/services/lifecycle.py` owns legal status transitions through `transition_subscription(...)` and `transition_invoice(...)`; related pause/resume/renew helpers also live here. Both HTML and JSON endpoints call these services. Do not use signals to bypass them.

Subscription standard path: DRAFT→QUOTATION→CONFIRMED→ACTIVE→CLOSED. Reversals/skips are rejected. Separate explicit early-close transitions from DRAFT/QUOTATION/CONFIRMED to CLOSED allow abandoning an unactivated offer, require an event, and do not generate bills. Active closure honors closable unless auto-expiry is the cause. Only admins/staff may confirm/activate. Activation requires today's date >= start_date; future confirmed contracts are activated by the billing run once due.

- Quotation requires complete valid lines and quote_expires_on. Template validity is copied when the quote is issued: expiry = issue date + validity_days; confirmation allowed through that date. Manual quotations use a visible default of 7 days, editable while draft.
- Confirmation freezes contract fields, checks quote validity and product/plan rules. Activation sets next_invoice_date=start_date, billing_anchor_date=start_date, index=0.
- Manual active close: collect all periods due up to the close request date first in the same service workflow; if billing cannot complete, fail closure with an actionable message. No refunds for an already begun period in the MVP; disclose in the confirmation dialog. Once closed, no future invoices. Existing debt remains payable.
- Auto-close: for auto_close contracts, bill outstanding eligible periods through expiry before closing after expiry. Paused intervals are not charged. For contracts without auto_close, show Expired and stop future billing at expiry; require close/renew. Expired contracts do not count as live active/MRR even if underlying status is ACTIVE.
- Pause: when allowed, settle previously due periods first, then mark is_paused and pause_effective_on=next_invoice_date (start of the next unpaid period). If next_invoice_date is None, there is no future billable period to pause; return a clear validation error. Existing purchased period remains usable through its end. No refund; no new invoices while paused. Until pause_effective_on arrives show “Pause scheduled”; thereafter show “Paused.”
- Resume before pause_effective_on: clear pause, retain anchor and next date. Resume on/after it: set new billing_anchor_date=today, period_index=0, next_invoice_date=today; paused gap is not invoiced. Original contract expiry stays; refuse resume after expiry. The truncated final period uses the rule in section 7.
- Renew: allowed if renewable and original is closed/expired or at its final service period. Create a new DRAFT, linked by renewed_from, copying lines and terms as editable offers. Default start=max(today, original expiry+1 day). Default expiry=one billing period from new start minus 1 day, editable before confirmation. For early-closed contracts default start=max(today, last purchased service end). Do not create overlapping service by accident. renewed_from is OneToOne: within a transaction return an existing successor on a repeated request instead of creating another; handle a uniqueness race by refetching. Later renewals operate on the latest successor, preserving a chain. If the successor was abandoned/closed before activation, show that fact and require staff to create a separate manual offer; do not silently reopen it.
- Portal renewal creates only the draft request; staff confirm/activate it. Show “Renewal requested,” not an already active renewal.

Templates: copy, never reference mutable template lines for financial values. Editing a template later must not alter an existing quotation. Plan must match the template; validate all copied quantities/products/variants. Teammate 1 owns template UI/copy helper; lead owns the actual lifecycle.

Invoice states: DRAFT→CONFIRMED→PAID; DRAFT/CONFIRMED→CANCELLED only if no payments. PAID is reached exclusively by payment service or confirmation of a zero-total invoice, using lifecycle helper. Partial payment leaves CONFIRMED. No reopening or deleting payments/paid invoices in MVP. A cancelled invoice retains its billing uniqueness key and redemption; it is not automatically rebilled. Refunds, credit notes, and replacement invoices are deferred and explicitly documented.

## 7. Billing dates and money

Billing is in advance. A period starts on next_invoice_date and is due when that date <= as_of. Periods are half-open [period_start,period_end); displayed expiry is inclusive. Clip the last end to expiry_date+1 day. Never create a zero-day period.

Daily = one calendar day; weekly = seven days; monthly/yearly use calendar arithmetic anchored to billing_anchor_date. Calculate boundary n from the original anchor and index, not from the previously clamped date: Jan 31→Feb 28/29→Mar 31; Feb 29 yearly anchors return to Feb 29 in leap years. Never approximate a billing month with 30 days.

If final expiry truncates a nominal period, prorate the line's recurring subtotal by actual service days / nominal period days. This is an explicit project decision for finite terms, not a general mid-cycle upgrade feature. Snapshot both day counts. Fixed per-invoice discounts apply to the resulting eligible subtotal, capped at that subtotal; do not separately prorate the discount.

All calculations:

```text
line_subtotal_paise = round_half_up(unit_price_paise * quantity * actual_days / nominal_days)
line_discount_paise = selected rule allocation, capped at line_subtotal_paise
taxable_paise = line_subtotal_paise - line_discount_paise
each_tax_paise = round_half_up(taxable_paise * rate_bps / 10000)
line_tax_paise = sum(each_tax_paise)
line_total_paise = taxable_paise + line_tax_paise
invoice totals = sums of the corresponding line fields
```

Use Decimal and quantize(Decimal('1'), rounding=ROUND_HALF_UP); cast to int only after rounding. Input currency conversion parses strings into Decimal and rejects excess fractional digits; never Decimal(float). Additive price-exclusive taxes only; tax-on-tax and jurisdictional tax advice are outside scope.

Example: unit ₹1,000 ×2, 10% discount, 18% tax, full period → subtotal ₹2,000, discount ₹200, taxable ₹1,800, tax ₹324, total ₹2,124. A variant surcharge of ₹560 becomes 56,000 paise.

## 8. Frozen service contracts for teammates

Use dataclasses or typed named structures; no free-form dict interpretation across owners. Put shared types in core/services/pricing.py before 13:00.

```text
BillingPeriod(start: date, end: date, nominal_end: date)
LineBase(source_line_id: int, product_id: int, quantity: int,
         unit_price_paise: int, subtotal_paise: int, taxes: list[TaxSnapshot])
DiscountApplication(discount_id: int, name: str, kind: str,
                    value_paise: int|None, value_bps: int|None,
                    line_discounts: dict[int,int], total_discount_paise: int)
BillingResult(created_ids: list[int], existing_ids: list[int],
              errors: list[str], remaining_due_count: int)
```

Services:

```text
get_applicable_discounts(subscription, period: BillingPeriod,
                         *, line_bases: list[LineBase]) -> list[DiscountApplication]
reserve_discount_usage(application, invoice) -> None
release_discount_usage(...)  # intentionally NOT part of initial build
create_invoice_for_period(subscription_id, period_start, *, as_of, actor=None) -> Invoice
run_due_billing(*, as_of, subscription_ids=None, max_periods_per_subscription=24, actor=None) -> BillingResult
transition_subscription(subscription_id, target, *, actor, reason='') -> Subscription
transition_invoice(invoice_id, target, *, actor=None, reason='') -> Invoice
record_payment(invoice_id, *, amount_paise, method, paid_on, note, idempotency_key, actor) -> Payment
get_invoice_balance(invoice_id) -> int
get_dashboard_summary(*, actor, filters, as_of) -> DashboardSummary
```

Morning offers/services/discounts.py stub returns [] and its reservation helper is a no-op that is never called without an application. Teammate 1 replaces both in the afternoon. Billing still implements zero/nonzero allocations and snapshots before 13:00. Teammate 1 does not rewrite the billing engine or alter signatures alone.

Define `DomainValidationError(code, message, field_errors=None)` in a shared core exceptions module; views translate it into preserved form errors or a structured 400 response. Permission checks use Django's PermissionDenied. Define `DiscountCapacityChanged` as a retryable service exception handled only outside the rolled-back period transaction. Do not swallow all exceptions into success notifications. Caller-supplied actor=None is allowed only for trusted scheduled/internal workflows; HTTP views always pass the authenticated user.

## 9. Transactional billing and discounts

### Billing algorithm

1. Capture as_of once; activate eligible confirmed contracts through lifecycle; select due, unpaused, unclosed contracts in stable ID order with next_invoice_date<=as_of and start<=expiry.
2. For each subscription, repeat up to the bounded catch-up limit. Each period uses its own short transaction, not one transaction for the whole company.
3. Enter an IMMEDIATE SQLite atomic transaction; reload subscription and validate due date/status/flags again. On PostgreSQL in a future deployment use explicit row locks; do not assume that backend is present now.
4. Derive current period from stored cursor/anchor; check unique(subscription,period_start). If an invoice exists, never create another or consume another discount use. Reconcile a stale cursor using the stored invoice.period_end and the documented anchor state; flag inconsistent cursor/anchor data instead of skipping blindly.
5. Build line bases from frozen contract unit prices and current tax rules, calculate terminal proration, call discount hook, choose its first deterministic application, create Invoice/InvoiceLines/InvoiceLineTaxes and snapshots, reserve discount use and write redemption, then advance cursor/index. All these changes commit or roll back together.
6. Discount reservation performs a guarded DB update: used_count=F('used_count')+1 with condition used_count<max_uses when capped, checking affected row count. A failed reservation rolls back the period and retries candidate selection from fresh state. SQLite serializes writers, but the guard remains essential to the contract.
7. After the final term, next_invoice_date=None. Close only when auto_close is due, through lifecycle. Every run includes a separate expiry-finalization pass so expired contracts with next_invoice_date=None or paused contracts are not missed by the due-invoice query. Finalize only after any eligible pre-pause backlog is settled. Advance only after success. A validation/DB error preserves the original cursor and appears in BillingResult.
8. Existing/cancelled invoice keys remain consumed; no implicit rebilling. IntegrityError from the uniqueness constraint is handled outside the failed atomic block by refetching existing state.
9. A SQLite locked/busy failure retries the whole period transaction at most three times with short bounded backoff outside atomic; after that report the error and leave it due. Do not hold a web request for unlimited catch-up.
10. If a catch-up limit is reached, leave cursor pointing at the earliest remaining unbilled period and show the backlog count. The next run continues. Do not skip dates. The web button uses a smaller batch/time budget; the command drains batches until done or a documented cap.

A button alone is not scheduling. Implement `run_billing` management command and document an optional local OS scheduler command running daily. Do not install a system scheduler without explicit authorization; demonstrate scheduled eligibility through the command and report whether a scheduler is actually configured. Invoice generation creates DRAFT invoices; staff confirm them. No emails inside the transaction; delivery is a separate action.

### Discount decisions and mechanics

- Automatic eligibility based on period.start, inclusive start/end dates, active rule, and unused capacity. A rule introduced later can affect a backdated catch-up period if its configured dates include that period; expose and document this behavior.
- PRODUCTS scope uses matching product lines. SUBSCRIPTION scope uses every line. min_purchase is eligible pre-tax/pre-discount subtotal; min_quantity is eligible total quantity. When both thresholds are nonzero, both must pass.
- Exactly one rule per invoice, no stacking. Select the rule with the greatest monetary saving; ties use lowest ID. This is a project assumption made to keep totals deterministic.
- Percentage discount: calculate rounded discount independently on each eligible line. Fixed discount: cap total to eligible subtotal and allocate proportionally by integer largest-remainder allocation, tie by source line ID; allocations must sum to the intended exact paise total.
- Never allocate more than a line subtotal; no negative taxable values. Zero-saving applications do not consume usage.
- One positive redemption consumes one use per invoice, not per line/seat. Duplicate runs do not increment again. Confirmation/cancellation does not change usage; refunds and restoring usage are outside scope.
- Discount rule edits must never change existing invoice allocations or redemption snapshots. DB and service protect an attempted max_uses change below used_count.

## 10. Payments, delivery, and dashboard definitions

### Payments

Outstanding = invoice.total_paise - sum(payment.amount_paise). Calculate from persisted rows, not a caller's balance. Accept only CONFIRMED invoices, positive amount<=current balance, known method, and paid_on<=today. A zero-total invoice becomes PAID on confirmation without inventing a payment.

Transaction: reload invoice and summed balance under the same writer lock; check UUID idempotency key before insertion. Identical replay returns the original payment; same key with different invoice/payload is a conflict. Insert payment; when remaining balance is zero call transition_invoice(PAID). Two concurrent submissions must not overpay. Partial payments keep CONFIRMED. No payment edits/deletes/refunds in initial UI.

Overdue is `status == CONFIRMED AND due_date < as_of AND balance > 0`; due today is not overdue. Draft/cancelled invoices do not enter receivables. Use query annotations/subqueries or separately aggregated sets to avoid multiplying totals when joining both invoice lines and payments.

### Send and print

Print route renders an invoice from stored identity/line/tax/discount snapshots, with number, period, issue/due dates, terms, totals, payments/balance, and status. Use a standalone print template; @media print hides navigation/actions and prevents obvious table row splitting. Browser print/save-as-PDF is sufficient for initial scope.

Send is an admin/staff POST on confirmed/paid invoices; use Django email with plain text and HTML. Use snapshotted billing email and an authenticated link to the invoice. Output via console or local file backend when offline. UI must explicitly say “Email written to local output” in local mode, not “Delivered.” SMTP mode can say “Handed to mail server,” never claim inbox delivery from send_mail return alone. Record sent_at after successful backend handoff; show errors without changing invoice totals/status. Customers can view/print own confirmed/paid invoices; internal draft/cancelled invoices stay out of portal lists.

### Dashboard

Definitions must be visible in tooltips/help:

- Revenue collected: sum of payments paid_on inside selected date range; label cash basis, not recognized revenue.
- Invoiced value: confirmed+paid invoice totals issued in range; optional secondary figure, distinct from cash.
- Outstanding: all confirmed invoice balances as of today, filtered by selected customer; date range does not silently remove old debt. Historical as-of accounting is not implemented.
- Overdue: outstanding confirmed balances with due_date<today; show count and amount.
- Active subscriptions: ACTIVE, start<=today<=expiry, not currently paused; “currently paused” means is_paused AND pause_effective_on<=today. A future scheduled pause still counts until that boundary. Customer filter applies. Label these as a current snapshot, unaffected by the payments date filter.
- MRR: sum normalized recurring pre-tax contract line values for the same active set, excluding one-time/temporary discounts and ignoring terminal partial-period adjustments. Daily×365/12, weekly×52/12, monthly×1, yearly÷12. Sum Decimal paise first then round once. This is a documented estimation convention, not calendar invoice calculation. Show “MRR before discounts”; show ₹0 for an empty set.

Filters: payment date range default current month, customer, subscription status for subscription table, invoice status for invoice table, search, page, allowlisted sort. Reject inverted dates and invalid enums; preserve filters during pagination. Show current-vs-range labels so totals reconcile.

Authenticated GET `/api/dashboard/summary/` returns the same selectors as HTML; money represented as integer paise plus currency, dates ISO strings. Customer role can receive own-account summaries only; no global data in response. This is the initial backend API scope; CRUD can remain server-rendered forms.

## 11. Routes and screen acceptance

| Namespace/routes | Screen and behaviors |
| --- | --- |
| /accounts/signup/, login/, logout/, password-reset/... | Branded compact auth card, inline validation, generic reset acknowledgement; logout POST |
| /team/ and /team/new/ | Admin-only staff list/create; no public role selector |
| /customers/, /customers/new/, /customers/<id>/edit/ | Staff/admin customer list/detail/form; customer account linkage protected |
| /catalog/products/, variants/, plans/, taxes/ | Searchable/paginated lists, new/edit/detail forms, archive action; role-protected writes |
| /subscriptions/, new/, <id>/, <id>/edit/ | Header, status stepper, customer/term panel, line table and totals, event trail |
| /subscriptions/<id>/{quote,confirm,activate,pause,resume,close,renew}/ | POST actions using lifecycle; action-specific dialog/text, server validation |
| /offers/discounts/ and /offers/templates/ | Admin list/detail/edit, valid-date and usage badges; staff read/use templates |
| /billing/run/ | Staff/admin POST; CSRF, disabled submit during request, counts/errors/backlog; no unbounded page request |
| /invoices/, /invoices/<id>/ | Filters, snapshot details, totals and payment history; actions based on state |
| /invoices/<id>/{confirm,cancel,send}/ and /invoices/<id>/print/ | POST mutations; print GET; permission and state enforced |
| /payments/ and /invoices/<id>/payments/new/ | Payment list and prefilled invoice payment form; fresh idempotency key on form render |
| /dashboard/ and /api/dashboard/summary/ | Current metric cards, range-based payment chart/table, overdue table and filters |
| /portal/ and /portal/subscriptions/<id>/, /portal/invoices/<id>/ | Own summary, subscriptions and invoices, plan-allowed close/pause/resume/renew, own print |

Lead mounts URL namespaces in S0; teammates only change their namespace's urls.py. Shared internal invoice detail/print may be reused by portal only through the same scoped access helper. Never add an unrestricted invoice URL as a shortcut.

## 12. UI design and motion specification

Design: calm financial workspace, local system fonts, clean spacing, plum navigation, teal highlights. Avoid a generic empty landing page: the first internal screen should be the dashboard/workspace and the first customer screen their account.

### Tokens

```css
:root {
  --bg: #f5f6fa; --surface: #ffffff; --text: #172033; --muted: #526078;
  --nav: #30243e; --primary: #674574; --primary-hover: #553860;
  --accent: #0b766e; --border: #dde2eb; --danger: #b42318;
  --warning: #8a4b08; --success: #146c43; --focus: #2563eb;
  --radius-card: 14px; --radius-control: 8px;
  --shadow-card: 0 4px 18px rgba(23,32,51,.06);
}
```

Spacing scale 4/8/12/16/24/32/48px. Body 14–16px, label 13–14px, heading 24–30px, metric 28–34px. Use tabular numerals for money. Minimum practical touch target 44×44px. Focus outlines must remain visible; verify contrast of actual components rather than assuming token values alone guarantee accessibility.

Desktop: 232px sidebar, 64px topbar, content max-width about 1440px, 24–32px padding. Sidebar: Overview; Customers; Products & Plans; Subscriptions; Invoices; Payments; admin Configuration grouped below. Customer sidebar: Overview, My Subscriptions, My Invoices, Profile. Use clear text labels with local SVG icons, no icon-only primary navigation.

Below 768px: sidebar becomes drawer with overlay, Escape close, focus returned to toggle; 16px content padding; metric cards stack; form columns collapse. Tables sit in labeled horizontally scrollable containers; do not cause full-page horizontal overflow. At 768–1100px use two-column cards, then four on larger screens.

Required shared components: title/breadcrumb/action header; metric card; labeled form field with adjacent error; primary/secondary/danger buttons; status badges with text; data table with sticky header when useful; pagination; empty state with real action; success/error message region; confirmation dialog; subscription stepper; invoice totals panel. Error states preserve typed data. Empty states must not contain fabricated financial totals.

Motion uses only opacity/transform and short CSS transitions:

- Page content appears over 160–200ms with opacity and translateY(4px), once per navigation.
- Cards/buttons hover over 120–160ms; no distracting tilt/bounce.
- Drawer opens over 180ms; status feedback over 150ms.
- Pending submit uses an inline spinner plus text and prevents accidental repeat click; backend idempotency remains required.
- Toast/message fades are optional; important errors remain until dismissed. Use aria-live politely for result messages.
- No animated currency counters, fake skeleton delays, continuously moving backgrounds, or heavy chart packages.
- `@media (prefers-reduced-motion: reduce)` removes animation/transitions and smooth scrolling; JS checks the same preference if it animates anything.

Use reusable CSS classes and components. Teammates add page-specific CSS in their own namespaced file loaded via a template block; only lead edits common CSS/JS. Main financial forms and all navigation work without JavaScript; JS enhances drawers/dialogs/previews. Never use client-calculated totals as authoritative.

## 13. Performance, seed data, and evidence

`seed_demo` is idempotent and non-destructive. It creates local-only admin/staff/two customer accounts, products with variants, four plan periods, a percentage tax, due/current/expired/paused subscriptions, draft/confirmed/paid/overdue invoices, and partial/full payments through domain services where feasible. Read demo password from environment or explicitly documented local-only defaults. Never reset existing real account passwords silently. Fixed example amounts must reconcile to section 7.

`seed_scale --subscriptions 5000` adds deterministic scale records under a recognizable demo namespace. Include invoice lines and enough payments/overdue balances to exercise reports; a table of subscriptions with no related records is not adequate. Use chunked bulk creation for scale fixtures only with explicit validation of invariants; do not call a simulated external mail sender. Do not add 5,000 users unnecessarily. Keep generated DB files out of Git.

Before 13:00 prepare/run a baseline on available routes; record missing dashboard routes as unavailable, not passed. Repeat around 14:30 after integration and once more only if relevant queries change. Use select_related for FK lists, bounded prefetch for displayed rows, SQL aggregate/subquery totals, and 25-row pagination. Never fetch all invoice lines/payments into every list view or compute cards by serializing 5,000 subscriptions to the browser.

`benchmark_pages`: authenticated local request measurements for dashboard, subscriptions, invoices, customer detail, portal; record seed counts, OS/Python/Django, machine context, route/filter/role, DB query count, cold sample and ten warm samples with median/max. Treat HTTP <2 seconds as a server-side check, not proof of full browser rendering. Also observe browser navigation with local assets on representative routes; record how measured. If only the backend was measured, say so. Bulk billing command runtime is reported separately from page navigation. Performance target remains a requirement until evidence exists.

## 14. Git ownership and integration

Branch names: lead `feature/spine`; teammate 1 `feature/offers`; teammate 2 `feature/finance`; teammate 3 `feature/insights-portal`. Begin afternoon branches from the same pushed spine commit. Do not share account credentials or author commits under someone else's identity.

Lead owns accounts/, config/, core/models/, all migrations, core/services/, catalog/, subscriptions/, common templates/static, root README/requirements. Teammate 1 owns offers/, templates/offers/, offer-specific tests/static. Teammate 2 owns finance/, templates/finance/, payment/delivery tests/static. Teammate 3 owns insights/, portal/, related templates/tests/static. Owners can request a shared change through a specific PR or message; lead applies shared schema changes first.

Morning creates all initial models, namespace stubs, and service contracts. Freeze schema at handoff. Schema changes after 13:00 are coordinated migrations with fresh dependency names; never edit an already-shared migration to hide divergence. Each feature owner owns their log to reduce documentation merge conflicts.

Commit roughly every 30 minutes or at a coherent completed increment. Each teammate reviews at least two meaningful PRs if enough PRs exist; do not create empty PRs to manufacture a metric. Small first PRs before ~14:00 establish real integration early. PR body: behavior, files/shared contract impact, checks performed, limitations, screenshots for UI, source/understanding note for substantial generated snippets. Only push/merge when authorized in the active work context.

## 15. Documentation contract and assumptions

Documentation must cover the whole event as it happens, not retrospectively invent a polished history. Each completed card/decision/blocker gets a timestamped entry; each merge updates the consolidated status. Use `docs/TEAM_HANDOFF.md` as the current operational view, per-owner logs as raw history, and `docs/HACKATHON_LOG.md` as evaluator-readable narrative.

Record decisions: stack, INR/paise, one primary product, no discount stacking, additive exclusive taxes, terminal proration, pause boundary, renewal as new draft, cash-basis revenue, gross-before-discount MRR, console-email fallback, cancelled invoice not rebilled. If changed, explain why, affected code/tests, and timestamp. Do not silently reinterpret the brief.

Sources for technical decisions:

- [Django 5.2 release and supported Python versions](https://docs.djangoproject.com/en/5.2/releases/5.2/).
- [Django SQLite transaction and locking notes](https://docs.djangoproject.com/en/5.2/ref/databases/#sqlite-notes).
- [Set the custom user model before initial migrations](https://docs.djangoproject.com/en/5.2/topics/auth/customizing/#substituting-a-custom-user-model).

The repository includes no application or test execution at planning time. Update that statement only as implementation and checks occur.
