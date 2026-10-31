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

