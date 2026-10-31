# Demo, checks, and evaluator evidence

Everything here is a planned check until an actual result is recorded. Do not pre-check boxes. Store generated evidence in docs/evidence/ and exclude secrets/customer data.

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
| Setup | Fresh install/migrate/seed/run; seed repeat safe | Not run |
| Auth | Case-insensitive email collision; exact password rule; reset flow | Not run |
| Access | Admin-only writes; direct endpoint checks; two-customer isolation | Not run |
| Catalog | Variant pricing, quantities, rates, availability and archive | Not run |
| Quotes | Independent template copy; validity deadline; status transitions | Not run |
| Lifecycle | Pause/resume/close/renew flags; expiry; dates; no overlap | Not run |
| Billing | Duplicate/concurrent run, rollback, catch-up, calendar anchor, final proration | Not run |
| Discounts | Scope/minimums/date boundaries, exact allocation, concurrent usage limit | Not run |
| Snapshots | Historical identity, prices, taxes and discount unchanged by edits | Not run |
| Payments | Partial/full, replay, concurrent overpay prevention, overdue | Not run |
| Send/print | Correct snapshot totals and ownership; honest delivery mode | Not run |
| Dashboard | Cash/outstanding/overdue/MRR reconcile; empty data and filters | Not run |
| UI | 390/768/1440px, keyboard, focus, reduced motion, useful errors | Not run |
| Offline | Local assets/db/email fallback; no network needed after install | Not run |
| Performance | 5,000 subscriptions plus related records; server and browser measurements | Not run |
| Git | Each contributor's actual branches, commits, PR reviews | Not available yet |

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

