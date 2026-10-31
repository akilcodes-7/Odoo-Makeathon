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

- Final commit/repository URL: pending.
- Implemented requirements and evidence: pending.
- Unfinished requirements: all build items pending at planning time.
- Measured performance and environment: pending.
- Verified demo/setup: pending.
- Team contributions/PRs: pending.
- Known limitations and follow-up work: pending.

