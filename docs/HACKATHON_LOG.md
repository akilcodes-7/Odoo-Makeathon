# Hackathon progress and decision log

All times are Asia/Kolkata (IST). Planned times are kept in the implementation plan; this file records actual events. A documentation timestamp is not a code implementation timestamp.

## 2026-10-31 09:36 IST — Planning checkpoint

- **Owner:** Lead planning assistant, working from participant instructions.
- **Completed:** Read the four-page subscription problem statement; incorporated participant-provided website must-have/nice-to-have rules; fixed Django/SQLite/templates stack; specified models, financial invariants, lifecycle, local UI/animations, ownership and documentation workflow.
- **In progress:** Task cards, current handoff, demo/check checklist, and contributor log templates.
- **Actual implementation:** None yet. No application checks run.
- **Decisions:** Solo until 13:00; separate teammate branches afterwards. Integer paise/Decimal calculations. Invoice uniqueness by subscription/period start. Atomic invoice+redemption+cursor. Local email fallback explicitly disclosed. MRR included by participant request.
- **Repository status:** Workspace started empty. Intended GitHub URL has not been supplied or verified.
- **Next:** Finish and inspect documentation package; then S0 scaffold and initial repository submission using the participant's intended destination.

## 2026-10-31 09:41 IST — Initial documentation package completed

- **Completed:** README, contributor instructions, detailed build specification, requirement matrix, bounded implementation task cards, current handoff, contributor log templates, demo/check checklist, evidence directory instructions, Git ignore rules, and PR template.
- **Review:** Checked internal Markdown links; no missing linked local files. Reviewed consistency of transaction boundaries, money/date rules, discount use, renewal idempotency, paused/expired reporting, and file ownership. This is a documentation review, not application verification.
- **Implementation/checks:** No application code created and no application tests or performance checks run.
- **Unfinished external action:** No Git repository initialized or GitHub destination pushed/submitted by this planning work.
- **Next:** Participant can commit/push the planning package to the intended repository; implementation begins with S0. Subsequent contributors must continue the logs as actual work occurs.

## 2026-10-31 09:43 IST — Hard deadlines incorporated

- **Source:** Participant supplied 09:00 repository-link submission, 10:00 evaluator access, 17:00 coding cutoff, and 17:30 video-link submission.
- **Changed:** Added deadline tracker with owners/evidence fields; replaced relative submission window; updated README, agent instructions, task cards, requirements, handoff and demo checklist; added V1 recording/submission task.
- **Status:** At this checkpoint the 09:00 time has passed; actual external submission is unknown, not confirmed missed. Local Git inspection reported this workspace is not a Git repository. Another team repository may exist.
- **Unverified:** Akilan's portal submission permission, exact portal instructions for `hapt-odoo`/`hackathon-odoo`, actual collaborator invitations/access, and submissions. Earlier portal access required login.
- **Next:** Responsible participant verifies repo submission immediately; repository owner handles evaluator access before 10:00. No external invitation, repository write, or portal submission was performed by this documentation update.

## 2026-10-31 09:53 IST — S0 implementation and verification

- **Owners:** Lead integrated three bounded S0 slices from model, scaffold and UI contributors; lead added seed/admin/service contracts and performed integration checks.
- **Implemented:** Django 5.2.18 scaffold; custom email User plus every initial domain model; initial accounts/core migrations and core constraints migration; configurable settings and local SQLite/email; 15 explicit empty-state routes; desktop shell, responsive CSS, role navigation, local JS, reduced-motion support; read-only financial admin views; idempotent local demo seed; paise/tax/billing dataclasses and empty discount hook.
- **Checks:** Fresh Python 3.12.14 venv `pip install -r requirements.txt`; Django `check` passes; migration dry-run reports no changes; fresh SQLite migrations all pass; demo seed creates three role accounts + customer, then repeat creates zero; all 15 placeholder route GETs return 200; admin/staff/customer shell conditions pass; admin product changelist returns 200; Python compile and `node --check` pass; local CSS finder resolves 3 files. Local browser desktop screenshot inspected at 876×720.
- **Limit:** Exact narrow/mobile browser viewport capture not done. Feature data flows, authentication, business workflow tests, and performance not implemented or verified. Placeholder screens state this plainly.
- **Environment:** Django installed in ignored `.venv/` after sandbox package DNS failure and successful approval; clean `.venv-verify/` installed from requirements. Verification DBs are in `/tmp`; no DB or environment directory is tracked. No local Git repository/remote exists and nothing was pushed.
- **Next:** No S1 work in this turn, per participant instruction. Update feature requirement status as future cards land.

## 2026-10-31 10:53 IST — S0 repository published on `dev`

- **Owner:** Lead / repository owner (`akilcodes-7`).
- **Changed:** Merged the evaluator-facing plan commit `21f5ab7` with the existing S0 project commit `68408ec` as `c914e43`. The branch now contains the Django project, models/migrations, local assets, requirements, setup README, task cards, full implementation specification, requirement matrix, deadlines, handoff, logs and demo checklist.
- **Push:** `c914e43` pushed to https://github.com/akilcodes-7/Odoo-Makeathon/tree/dev and verified by remote ref. Only `dev` was updated; the existing remote default branch was left unchanged.
- **Checks:** Confirmed the branch tree includes all 98 project files and the plan README; no application code was changed in this repository publication step.
- **Limit:** The app remains at S0; feature pages are placeholders. Portal submission and evaluator collaborator invitations are unverified.
- **Next:** Teammates branch from `dev`; continue with the next explicitly assigned card.

## 2026-10-31 11:23 IST — Feature workflow integration and scale verification

- **Owner:** Lead integration; implementation slices were delegated to agents in the shared checkout. No human contributor identity, review, or Git activity is attributed by this entry.
- **Implemented:** S1 authentication/reset and role enforcement; S2 catalog forms; S3 subscription drafts/lifecycle and quotation template copy; S4 recurring invoice billing/state helpers and command; T1A discount rules and T1B template CRUD/picker; T2A payment recording and T2B send/print; T3A dashboard/API and T3B scoped portal; S5 repeat-safe `seed_scale` and authenticated `benchmark_pages`. Added customer detail and improved portal dashboard balances with SQL aggregation after the scale run found an N+1.
- **Checks:** `manage.py test` found 92 tests and passed, with 3 concurrency tests skipped because that run used Django's shared in-memory SQLite. `TEST_DATABASE_PATH=/tmp/brightloop-concurrency.sqlite3 manage.py test tests.test_concurrency` separately passed all 3: concurrent duplicate billing, one-use discount reservation, and overpayment attempts. `manage.py check`, migration drift check, `git diff --check`, and `node --check static/js/app.js` passed. Fresh temporary DB migration/seed passed; scale command added 5,000 subscriptions, 5,000 invoices, 5,000 lines and 2,500 payments.
- **Performance:** At 11:22 IST on macOS 26.7.1 arm64, Python 3.12.14, Django 5.2.18, SQLite, ten warm local Django test-client requests per route: dashboard 0.0206s median/0.0215s max (16 queries); subscriptions 0.0033/0.0041s (4); invoices 0.0030/0.0034s (4); customer detail 0.0021/0.0022s (5); portal 0.0046/0.0049s (8). All passed the <2s backend target. This excludes browser render/paint, network latency and concurrent load. An initial harness attempt failed with disallowed `testserver`; a second used a nonexistent `/dashboard/` path. The host and root dashboard path were corrected before the successful run.
- **Remote/Git:** Read-only remote inspection confirmed `dev` remained `4ac7968` and default branch remained `plan-submission-17140653490169652980`; neither was changed. Work is on local `codex/remaining-core`; no code commit, merge, or push yet. Feature implementation remains unpushed pending coherent review/integration. Genuine human Git contribution evidence is not available.
- **Limits/next:** Browser visually inspected at available 890×921 only. Exact 390/768/1440 screenshots, full keyboard/contrast audit, fresh remote clone check, SMTP receipt, background scheduler, evaluator portal submission/access and video submission are unverified. Next: complete responsive review if available, inspect final diff, make transparent local commits, merge/push to `dev` only while the verified remote state and 17:00 cutoff still allow; record external submission status only from the authorized submitter.

## 2026-10-31 11:24 IST — Lifecycle edge checks and final suite refresh

- **Changed:** Added lifecycle tests for expired quote rejection, pause settling the current period, resume before/after the pause boundary, re-anchoring, early-close renewal start, and idempotent renewal. Added optional on-disk SQLite test database support so thread-based concurrency checks can run outside SQLite's in-memory shared-cache limitation. Increased the current admin logout and menu touch target to 44px and added the internal customer detail route used by the scale benchmark.
- **Checks:** Latest full suite discovered 95 tests and passed with the three on-disk concurrency cases skipped in in-memory mode. Dedicated on-disk concurrency command had already passed all three. `manage.py check`, `makemigrations --check --dry-run`, `git diff --check`, and `node --check static/js/app.js` passed.
- **Limitations:** No 390/768/1440 screenshot; no actual email transport receipt, background scheduler, browser-render timing, or human Git contribution/review evidence. Remote `dev` and default were read before implementation integration; no branch merge/push was performed yet.
- **Next:** Final diff review; commits and local/remote integration on `dev`, with no default-branch writes; preserve cutoff at 17:00 IST.

## 2026-10-31 11:26 IST — Quote expiry acceptance and final focused checks

- **Changed:** Added a visible editable quotation expiry field to manual draft forms with the specified seven-day initial value. Template-backed quotes continue to use the selected template's validity at issue time. Added a view assertion for both manual default/editable behavior and preserved template expiry behavior.
- **Checks:** Latest full suite found 96 tests and passed; 3 concurrency tests skipped in in-memory mode. The dedicated on-disk concurrency suite passed 3/3. `manage.py check`, migration drift check, `git diff --check`, and JS syntax passed. Combined subscription/template view check passed 11/11.
- **Limitations/next:** Exact responsive viewport checks and visual/accessibility review remain incomplete. Final Git commits/merge/push and external submission evidence remain pending.

## 2026-10-31 11:27 IST — Integrated implementation committed locally

- **Branch/commit:** `codex/remaining-core`, commit `0b436d9a9495fe99f43b929224301603935a6687` (`feat: implement Brightloop subscription workflows`). Commit uses the repository-configured author; it is a local automation-assisted integration commit, not a teammate PR/review.
- **Contents:** 120 application, template, static CSS and test files; no database, virtualenv, generated cache, or credentials.
- **Verification before commit:** Full test suite (96 discovered, pass, 3 concurrency skips in in-memory mode); separate on-disk concurrency suite (3 pass); Django check; no-migration check; `git diff --check`; JS syntax.
- **Git state:** Remote `dev` had just been fetched and exactly matched local `dev` at `4ac7968`; default branch remains separate. Commit is not pushed or merged yet. Documentation evidence remains modified for its own commit.
- **Next:** Commit the documentation update, re-fetch `dev`, fast-forward local `dev` only if it still matches the verified base, then push the authorized task branch and `dev` if authentication is available and cutoff allows.

## 2026-10-31 11:29 IST — Integrated branch pushed and verified

- **Integration:** Re-fetched remote immediately before merge; `origin/dev` still matched `4ac7968`. Fast-forwarded local `dev` from the feature branch, preserving commit history.
- **Push:** Pushed `codex/remaining-core` and `dev` to the requested repository. Remote read-back showed both at `cee28fb908ea88e96f3500ffaab172f32d20fa64`; default `plan-submission-17140653490169652980` remained at `ca69b4b330e75d4070b92376993df74b2200c5db` and was unchanged.
- **Commits:** Implementation `0b436d9a9495fe99f43b929224301603935a6687`; documentation `cee28fb908ea88e96f3500ffaab172f32d20fa64`. Both use the repository-configured Git identity; no separate teammate identity or review is claimed.
- **Next:** Record this remote verification in the handoff, commit/push that docs-only update to both authorized branches, and retain remaining visual/external submission limitations.

## 2026-10-31 11:32 IST — Fresh clone setup and test verification

- **Setup:** Cloned the pushed `dev` branch into `/tmp/brightloop-fresh-clone`; using the workspace Python 3.12.14 interpreter, installed `requirements.txt`, migrated a fresh SQLite database, and ran `seed_demo` twice (first created 3 accounts, second created 0 duplicates).
- **Checks:** Fresh clone `manage.py check`, `makemigrations --check --dry-run`, and full suite passed; 96 tests passed and 3 concurrency tests skipped under the default in-memory test DB. Dedicated on-disk concurrency results remain 3 passed from the integrated checkout. Initial system `python3.12` lookup and sandbox DNS install failed; both were resolved with the existing 3.12 interpreter and authorized network retry.
- **Scope:** This verifies the pushed `dev` snapshot before the current docs-only update; no implementation files changed. Temporary clone/database remained outside Git.
- **Next:** Commit the recorded setup evidence, re-fetch and fast-forward only if `dev` remains unchanged, then push task branch and `dev`, read back refs, and clean temporary files.

## 2026-10-31 11:51 IST — Functional audit found acceptance failures

- **Scope:** Read-only application audit at local `dev` commit `32f797d`; delegated independent lifecycle/billing and access/view reviews, plus integrated checks and isolated endpoint/form probes. No application code or demo data changed.
- **Findings:** Ten reproduced defects recorded in `docs/AUDIT_2026-10-31.md`. Highest priority: stale draft save reverts confirmation, tax editing divides rates twice, failed forms alter money/rate inputs, and product creation never binds POST data. Other defects cover malformed plan IDs, archived confirmation, final-period renewal, paused auto-close and billing date/error handling.
- **Checks:** Full suite: 96 discovered, 93 passed, 3 skipped (13.772s); separate on-disk concurrency suite: 3 passed (0.281s). Django check, migration drift, JS syntax and whitespace checks passed. Agent focused suite passed 41 (overlapping full-suite coverage). Isolated probes demonstrate scenarios omitted by those tests.
- **Documentation:** Added audit report and qualified earlier completion claims in README, requirement traceability, demo evidence and handoff. No fixes, commits, pushes or submission were made during this audit.
- **Next:** Resolve A01–A04 first, then remaining confirmed defects and UI/seed acceptance gaps before the coding cutoff. Do not mark functionality complete from the old test suite alone.

## 2026-10-31 12:02 IST — Single shared `dev` team handoff

- **User decision:** Use the existing lowercase `dev` branch as the shared team branch and retain the repository's current default. Other branches are preserved.
- **Remote check:** `git ls-remote --symref` and a fresh `git fetch origin dev` showed `dev` at `32f797d`, matching local `dev`. Default remained `plan-submission-17140653490169652980` at `ca69b4b`.
- **Prepared:** The single `docs/REPAIR_AND_UI_REDESIGN_PLAN.md`, functional audit, corrected completion claims and team clone/ownership instructions for publication on `dev`.
- **Scope:** Documentation only. No defect fixes, UI implementation, deployment or portal submission. Repair/redesign status remains planned.
- **Next:** Commit the docs through the existing task branch, fast-forward `dev`, push only `dev`, then read back refs and check the working tree. Teammates start from `dev` and assign work from the single plan.

## Entry template

Copy this for actual progress; replace all placeholders and remove irrelevant lines:

```text
YYYY-MM-DD HH:MM IST — Card/decision title
Owner:
Card / branch:
What changed and why:
Checks actually run and results:
Evidence / commit / PR:
Blockers / known limitations:
Next action and owner:
```

## Decision register

| ID | Decision | Reason | Status |
| --- | --- | --- | --- |
| D01 | Django 5.2, Python 3.12, SQLite, templates, local CSS/JS | Fits participant stack, local demo and short timeline | Planned architecture |
| D02 | Integer paise; Decimal calculations; single INR currency | Exact stored sums and explicit rounding | Planned |
| D03 | One invoice per subscription/period_start; transactional cursor and usage | Prevent duplicate billing and overspent discounts | Planned |
| D04 | One best discount per invoice, no stacking | Deterministic interpretation of unspecified stacking | Project assumption |
| D05 | Plan price is primary-product unit price | Avoid charging both plan and product for the same entitlement | Project assumption |
| D06 | Additive exclusive taxes; discount before tax | Explicit consistent arithmetic for the demo | Project assumption |
| D07 | Calendar billing anchor; final-term day proration | Handle month ends/leap years/finite expiry explicitly | Project assumption |
| D08 | Pause at next unbilled boundary; resume reanchors after pause | Avoid invoicing paused gaps or refund complexity | Project assumption |
| D09 | Renew into an independently confirmed draft | Retain history and keep changes reviewable | Project assumption |
| D10 | Cash collected revenue; MRR before discounts | Distinguish cash from recurring contract value | Project assumption |
| D11 | Console/file email offline; SMTP optional | Enable local demo without claiming real delivery | Local fallback |
| D12 | Cancelled invoice retains period key and discount use | No silent rebilling or undocumented refund logic | Project assumption |
| D13 | Genuine Git identities/PRs; timestamped logs | Make participation and progress reviewable | Required workflow |

## End-of-event record — complete later

- Final implementation commit/repository: `0b436d9` on https://github.com/akilcodes-7/Odoo-Makeathon, integrated into `dev`; docs through `c9638c8` were read-verified, and this fresh-clone follow-up records the separate docs-only push.
- Implemented requirements and evidence: S0–S5, T1A/B, T2A/B, and T3A/B are implemented; see `docs/REQUIREMENTS.md` and `docs/DEMO_AND_CHECKS.md`.
- Unfinished requirements: exact 390/768/1440 screenshots and full keyboard/contrast audit; external portal receipt, evaluator invites, and video submission are unverified.
- Measured performance: five authenticated server-rendered routes under 2 seconds at 5,000 subscriptions with related invoices/lines and payments; environment and per-route results in `docs/DEMO_AND_CHECKS.md`.
- Verified demo/setup: fresh clone install/migrate/seed repeat/full suite passed; 96 tests passed with 3 in-memory concurrency skips; separate on-disk concurrency checks passed 3.
- Team contributions/PRs: delegated implementation plus lead integration; repository-configured Git identity used; no separate human teammate commits or PR reviews are claimed.
- Known limitations: no browser timing, external scheduler, live payment gateway, refunds, credit notes, confirmed email receipt, or external portal/video evidence.


## 2026-10-31 14:27 IST — I1 evaluator-ready repository startup

- **Implemented:** Standard-library `scripts/run_demo.py` creates a venv, installs pinned Django, migrates an isolated persistent `.demo/db.sqlite3`, generates private local credentials, seeds four role-based accounts and eleven subscriptions, and starts localhost. Fresh seed contains six invoices and three payments. Repeat startup preserves account edits/passwords and records. `seed_evaluation` creates quote, due-billing, partial-payment, renewal and scheduled-pause scenarios via existing services.
- **Files:** launcher, `core/management/commands/seed_evaluation.py`, `tests/test_evaluation_workflow.py`, billing index route/view, base/payment templates, `.gitignore`, README and evaluator guide; integration handoff/check logs updated. Staff quotation templates, admin team accounts and payment-entry navigation are discoverable. No shared models, migrations or lifecycle signatures changed.
- **Checks:** Four evaluator workflow tests passed (real login and POST forms with CSRF, quote through full payment, repeat billing, email generation, customer isolation, signup/staff creation, renewal/resume and seed preservation). Full suite: 127 discovered, 124 passed, 3 in-memory concurrency skips (17.553s). Separate temporary on-disk concurrency suite: all 3 passed (0.290s). Django check, migration drift and diff whitespace pass. Fresh source copy with a new venv installed dependencies, migrated, seeded and passed checks; repeat startup preserved an edited staff name, password hashes and subscription count. Initial sandbox DNS prevented dependency install; authorized network retry succeeded. Browser login, populated dashboard, payments CTA and team controls verified at 1280×720.
- **Git/context:** Based on published `Main` commit `2ded2a6`; earlier `41ebeea` contains audit repairs and `0e5595b` UI changes. Old audit/open-status text is historical, not a fresh finding against this build. This entry records checks before committing the evaluator update.
- **Limits/next:** Local manual billing and manual payment recording; invoice/reset emails go to local files. No live gateway or external email delivery. Windows invocation is documented but not executed. Exact 390/768/1440 viewport, keyboard/reduced-motion acceptance and external submission/access/video evidence remain outstanding. Publish the tested update to Main, then rehearse using `docs/EVALUATOR_GUIDE.md` before the cutoff.

## 2026-10-31 15:26 IST — T3A dashboard and public-page polish

- **Changed:** Added a local CSS polish layer, collapsible dashboard filters, MRR/overdue KPI emphasis, count-up animation, visual daily-collections bars based on the table, and status badges. Public authentication pages hide the staff sidebar. Financial values remain rendered server-side; the animation and bars read only existing integer-paise values and use Indian digit grouping.
- **Files:** `static/css/polish.css`, `static/js/polish.js`, `templates/base.html`, `templates/insights/dashboard.html`, `templates/registration/login.html`.
- **Checks:** `.venv/bin/python manage.py check` passed; `node --check static/js/polish.js` passed; `git diff --check` passed. Browser inspection confirmed dashboard metrics/tables and filter collapse/expand; screenshot confirmed the centered public login without staff navigation. No automated tests were run.
- **Limitations/next:** Narrow viewport, keyboard, reduced motion and dashboard screenshot-level review remain incomplete. Continue responsive review before the 17:00 code cutoff if time allows.
