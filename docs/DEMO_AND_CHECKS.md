# Demo, checks, and evaluator evidence

The entries below record actual local checks from 2026-10-31. No external portal or video submission is represented as complete. No generated database or secret is stored in Git.

## Hard deadlines and initial repository submission

See [deadline owners and status](DEADLINES.md). Repository URL was due 09:00 IST; collaborator access is due 10:00; coding stops 17:00; video URL is due 17:30 on 2026-10-31. Earlier relative 20-minute planning estimates no longer determine submission times.

- [ ] README clearly states actual implementation status.
- [ ] Plan, task cards, requirements, and handoff are committed under the actual author's identity.
- [ ] Intended GitHub repository exists and contains the correct pushed commit.
- [ ] Repository URL opens for the evaluator's expected access level.
- [ ] Participant reviews any portal-specific initial submission requirements.
- [ ] Actual repository URL submitted through the correct portal workflow.
- [ ] Submission receipt/time recorded, if available.
- [ ] Portal submission permission verified; Akilan is provisional owner, not confirmed solely from leader-only problem-edit permissions.
- [ ] Repository owner has handled `hapt-odoo` and `hackathon-odoo` collaborator access by 10:00, unless portal instructions differ.
- [ ] Invitations sent and accepted/access-active statuses distinguished; actual times recorded.

Creating local documents does not complete these remote submission steps.

## Verification matrix

| Area | Minimum meaningful checks | Actual result/evidence |
| --- | --- | --- |
| Setup | Fresh install/migrate/seed/run; seed repeat safe | Fresh `/tmp/brightloop-scale.sqlite3` migration passed; `seed_demo` created 3 local accounts; `seed_scale --subscriptions 5000` created 5,000 subscriptions, invoices and lines plus 2,500 payments. Seed repeat is covered by `tests.test_seed_scale`; all local DBs remained outside Git. |
| Auth | Case-insensitive email collision; exact password rule; reset flow | `tests.test_auth`: 7 tests passed, including normalized duplicate email, password rule, reset token one-use, and POST+CSRF logout. |
| Access | Admin-only writes; direct endpoint checks; two-customer isolation | Auth, catalog, team, customer, payment, template and portal access tests pass; portal foreign IDs return 404. Full suite below. |
| Catalog | Variant pricing, quantities, rates, availability and archive | `tests.test_catalog`: 10 tests passed, including paise conversion, variant-product matching, tax basis points, eligibility and archive behavior. |
| Quotes | Independent template copy; validity deadline; status transitions | `tests.test_templates` (6) and subscription view tests (4) passed; template edits do not change copied lines, template validity sets quote expiry, expired quote cannot confirm. |
| Lifecycle | Pause/resume/close/renew flags; expiry; dates; no overlap | `tests.test_lifecycle`: 6 tests passed for legal transitions, snapshots, expired quotes, pause settlement, resume boundary reanchor and idempotent renewal. Portal flag/ownership tests also pass. |
| Billing | Duplicate/concurrent run, rollback, catch-up, calendar anchor, final proration | `tests.test_billing` passed with duplicate period, cursor, bounded catch-up, rollback, tax and terminal proration checks. `tests.test_concurrency` passed separately on an on-disk SQLite test database: same-period concurrent billing created one invoice and advanced once. |
| Discounts | Scope/minimums/date boundaries, exact allocation, concurrent usage limit | `tests.test_discounts` (12) passed. Concurrent competing invoices in `tests.test_concurrency` reserved the max-use-one discount once. |
| Snapshots | Historical identity, prices, taxes and discount unchanged by edits | Billing/discount/template/delivery tests confirm saved snapshots remain stable under source edits and render from saved invoice data. |
| Payments | Partial/full, replay, concurrent overpay prevention, overdue | `tests.test_payments` (5) passed; on-disk concurrency suite confirmed two distinct 7,000-paise attempts against a 10,000-paise balance result in only one payment. |
| Send/print | Correct snapshot totals and ownership; honest delivery mode | `tests.test_delivery` (4) passed for sendable states, address/backend failure, snapshot print and customer isolation. Configured email backend is console by default. |
| Dashboard | Cash/outstanding/overdue/MRR reconcile; empty data and filters | `tests.test_reporting` (4) passed for hand-calculated metrics, customer scope, invalid filters and empty values. Scale benchmark found and led to removal of portal dashboard N+1 balance queries (206 to 8). |
| UI | 390/768/1440px, keyboard, focus, reduced motion, useful errors | Local browser rendered customer dashboard at its available 890×921 viewport. CSS/JS implement responsive drawer, Escape/focus handling, 44×44 menu target, and reduced motion. Exact 390/768/1440 screenshots and full keyboard/contrast audit remain unverified. |
| Offline | Local assets/db/email fallback; no network needed after install | Static styles/scripts are local; Django console email default. Fresh offline install was not tested (dependency packages may require package access). |
| Performance | 5,000 subscriptions plus related records; server and browser measurements | Backend measurement passed all five routes under 2s; details below. Full browser rendering and concurrent load were not measured. |
| Git | Each contributor's actual branches, commits, PR reviews | Remote refs read after push: `dev` and `codex/remaining-core` both `cee28fb`; default=`plan-submission-17140653490169652980` unchanged. Implementation commit `0b436d9` and docs commit `cee28fb` use repository-configured author. No PR/review or separate human teammate commits are recorded. |

## Integrated verification — 2026-10-31

- Latest `./.venv/bin/python manage.py test --verbosity 1`: 96 tests discovered, suite passed; 3 concurrency tests were skipped because this default run uses Django's shared in-memory SQLite test database. The dedicated on-disk concurrency suite passed all 3.
- `TEST_DATABASE_PATH=/tmp/brightloop-concurrency.sqlite3 ./.venv/bin/python manage.py test tests.test_concurrency --verbosity 1`: 3 concurrent billing, discount-capacity, and distinct-payment tests passed against the temporary on-disk SQLite database.
- `manage.py check`: passed with zero issues.
- `manage.py makemigrations --check --dry-run`: passed; no migration changes detected.
- `git diff --check`: passed. `node --check static/js/app.js`: passed.
- `tests.test_subscription_views` (5) and `tests.test_templates` (6): passed after adding visible editable manual quote expiry with a seven-day default and verifying the template validity override.
- Initial benchmark harness attempts returned HTTP 400 because Django's test client used disallowed host `testserver`; after using allowed `localhost`, `/dashboard/` returned 404 because the dashboard is mounted at `/`. The harness now uses `/`; final successful results follow. These were harness/path errors, not route performance results.

## Performance record — 2026-10-31 11:22 IST

Recorded with `manage.py benchmark_pages --warm-samples 10` on macOS 26.7.1 arm64, Python 3.12.14, Django 5.2.18, SQLite, 5,000 subscriptions, 5,000 invoices, 5,000 invoice lines and 2,500 payments. Routes were authenticated local Django test-client GET requests; timings include server-side rendering but not browser layout/paint or network latency. The browser itself was visually inspected at its available 890×921 viewport, but no browser-navigation timing was collected.

| Route / role | HTTP | Cold time / queries | Warm query count | 10 warm requests: median / max | Under 2s |
| --- | --- | --- | --- | --- | --- |
| Dashboard `/` / admin | 200 | 0.0431s / 16 | 16 | 0.0206s / 0.0215s | Pass |
| Subscriptions `/subscriptions/` / admin | 200 | 0.0044s / 4 | 4 | 0.0033s / 0.0041s | Pass |
| Invoices `/invoices/` / admin | 200 | 0.0039s / 4 | 4 | 0.0030s / 0.0034s | Pass |
| Customer detail `/customers/1/` / admin | 200 | 0.0033s / 5 | 5 | 0.0021s / 0.0022s | Pass |
| Portal `/portal/` / customer | 200 | 0.0064s / 8 | 8 | 0.0046s / 0.0049s | Pass |

Times are local single-process checks on this machine; they do not establish production capacity. The initial portal measurement was 206 queries; balance subqueries/aggregates reduced it to 8 before this final run.

## S0 verification checkpoint — 2026-10-31 09:53 IST

| Check | Actual result |
| --- | --- |
| Requirements install in fresh Python 3.12.14 venv | Passed; installed Django 5.2.18 and its transitive requirements |
| `manage.py check` | Passed, zero issues |
| `manage.py makemigrations --check --dry-run` | Passed, no model changes pending |
| Fresh SQLite migration | Passed through accounts/core including the constraints migration |
| `seed_demo` twice | Passed; first run created three role accounts and a linked customer; second run created zero duplicates |
| URL/render smoke | Passed; 15 placeholder routes returned HTTP 200 |
| Role shell smoke | Passed; admin config link, staff without config link, customer portal menu |
| Django admin read view | Admin product changelist returned HTTP 200 |
| JavaScript syntax | `node --check static/js/app.js` passed |
| Static CSS | Three local CSS files resolve through Django static finder; no external font/icon dependency in shell |
| Desktop appearance | Inspected in a local browser; clean 876×720 preview; screenshot was not saved |
| Mobile appearance | Responsive breakpoints/code present; narrow viewport visual check still pending |

This checkpoint covers S0 only. No authentication/product/billing/discount/payment/reporting/portal flow or performance benchmark is verified.

Focused tests should assert business outcomes, not implementation internals. Concurrency tests need genuinely separate DB connections and a shared test database; an isolated in-memory database per worker is not a valid shared-writer test. Use TransactionTestCase or a dedicated temporary on-disk test DB as appropriate; never run destructive concurrency checks on the demo database.

## Performance record format

```text
Recorded at (IST):
Commit:
Machine/OS:
Python/Django:
DB/backend and actual row counts:
Endpoint, user role, filters:
Cold response time:
10 warm times, median, maximum:
Query count / observed N+1 problems:
Browser navigation measurement method and result:
Pass/fail against under-2-second requirement:
Limitations (for example localhost, no concurrent load):
```

Do not call a cached browser view or one empty-database request proof of the performance requirement. Preserve failing measurements and subsequent fixes instead of replacing history silently.

## Five-minute demonstration script

Prepare known seed data and an overdue subscription; do not spend demo time constructing every fixture.

1. **0:00–0:40 — Context and admin:** Log in as admin. Show product, +₹560 variant, plan schedule/flags, tax and discount. Mention local persistent data.
2. **0:40–1:40 — Quote to subscription:** Log in as staff or use prepared session. Pick customer/template, show lines/validity/terms, move quotation through confirmation to activation.
3. **1:40–2:30 — Billing correctness:** Run billing, show resulting invoice and tax/discount totals. Run again; show no duplicate. If time allows show caught-up periods with distinct period starts.
4. **2:30–3:20 — Collection:** Confirm invoice; record partial payment, show balance; record remaining payment, show PAID. Open print view. Disclose console/file email when demonstrating Send.
5. **3:20–4:10 — Customer isolation:** Log in as customer, show own invoice/subscription, allowed renewal/close action. Demonstrate a prepared forbidden foreign-record URL returning no access.
6. **4:10–5:00 — Business view and evidence:** Show cash collected/outstanding/overdue/MRR, filters, measured scale results, team contribution history, and known limitations.

Keep credentials in the documented local demo instructions; no real passwords visible in screenshots. Avoid claiming a live payment gateway, real email delivery, background scheduler, or performance result unless implemented and verified.

## Final evaluator handoff

All final code changes/merges/pushes finish before 17:00 IST. Target video submission by 17:25, five minutes before the 17:30 hard deadline; see V1 task card.

- [ ] README has exact tested setup commands, dependencies and demo accounts.
- [ ] Requirement table matches actual scope.
- [ ] Logs contain actual work times and decisions.
- [ ] Screenshots show implemented screens, not only mockups.
- [ ] Check results/performance include environment and date.
- [ ] Final commit and meaningful PR links recorded.
- [ ] Email backend, scheduler and internet dependencies disclosed.
- [ ] Incomplete requirements and follow-up work listed plainly.
- [ ] Final code commit frozen and pushed before 17:00.
- [ ] Video length/platform follow verified portal instructions.
- [ ] Uploaded video plays for intended viewers.
- [ ] Akilan/verified submitter saved the video URL before 17:30; receipt/time recorded.

