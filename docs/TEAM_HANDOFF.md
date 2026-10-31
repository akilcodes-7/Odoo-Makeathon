# Current handoff — read this first at 1 pm

**Last recorded update:** 2026-10-31 09:53 IST. This update records S0 implementation/checkpoint results; it does not mean the later hackathon cards are complete.

## Deadline actions first

[Hard deadline tracker](DEADLINES.md): 09:00 repo-link submission; 10:00 evaluator access; 17:00 coding ends; 17:30 video submission. The 09:00 time has passed; portal submission status is unknown. Verify with Akilan/the portal immediately. Repository owner handles the two requested evaluator handles before 10:00. Akilan is the provisional portal submitter; verify actual permissions.

## Actual state

- S0 scaffold, model schema, initial/core migrations, local seed command, Django shell and namespace placeholder routes are implemented.
- `check`, migration drift check, fresh DB migration, repeat seed, 15 route renders, role menu/Admin access smoke checks, local CSS discovery, JS syntax, and desktop visual review passed. Exact narrow viewport/mobile screenshot remains unverified.
- S1 and all product feature tasks remain unstarted: auth/permissions, catalog CRUD, subscriptions, billing, discount application, payments, dashboard, and portal data views.
- `/tmp` was used for test databases. No test DB is committed; the project root default `db.sqlite3` remains unseeded.
- `core/migrations/0001_initial.py` plus `0002_...` contain shared schema constraints; accounts uses `0001_initial.py`.
- `requirements.txt` pins Django 5.2.18. `.venv/` and `.venv-verify/` are local ignored environments, Python 3.12.14.
- No GitHub repository URL or pushed base commit has been supplied/verified in this chat. This workspace has no `.git` directory.
- A desktop browser screenshot was inspected but not saved as an evidence file. No 5,000-record benchmark is run.
- Teammates are unavailable for implementation before 13:00 IST. Portal administration deadlines still require the responsible submitter/owner to act earlier; do not defer those to the coding handoff.

## Owner board

| Owner | Branch target | Cards | Actual status | Blocker/next action |
| --- | --- | --- | --- | --- |
| Lead / repo owner | feature/spine | S0–S5, I1 | S0 implemented; one viewport verification pending | Do not begin S1 until the participant requests it; prioritize remaining external deadlines separately |
| Teammate 1 | feature/offers | T1A, T1B | Not started; joins after 13:00 | Needs pushed schema and discount hook |
| Teammate 2 | feature/finance | T2A, T2B | Not started; joins after 13:00 | Needs invoice models and lifecycle helper |
| Teammate 3 | feature/insights-portal | T3A, T3B | Not started; joins after 13:00 | Needs scoped selectors, models and lifecycle helper |
| Akilan (provisional portal submitter) | N/A | Submission, V1 | External status unknown | Verify 09:00 repo submission and submit video by 17:30 |

## Fill these from verified implementation before handoff

| Item | Actual value |
| --- | --- |
| GitHub repository | Not provided |
| Shared base commit | Not created/verified; this workspace has no Git repository |
| Python/Django exact versions | Python 3.12.14, Django 5.2.18 |
| Fresh setup commands | README updated and venv install from requirements verified |
| Demo credentials | Seed command prompts securely; shared local password not stored |
| Working URLs | 15 honest S0 placeholder routes return HTTP 200 locally; feature workflows unavailable |
| Failing checks | None after integration; see timestamped test run in progress log |
| Known code defects | Exact narrow/mobile viewport visual check pending; no feature implementation yet |
| Email mode | Console backend configured by default; reset/email flows not implemented |
| Scheduler | No billing command/scheduler yet |
| Performance evidence | Not measured |

## Integration checklist before teammates branch

- [ ] Complete initial models including discounts/templates/payments and snapshot records.
- [ ] Confirm custom user model is in the first accounts migration.
- [ ] Mount namespace routes and feature template directories.
- [ ] Commit the shared discount dataclasses and stub signature.
- [ ] Commit invoice state helper and balance/payment contract.
- [ ] Record lifecycle helpers the portal must call.
- [ ] Push base commit; every teammate branches from it using their own identity.
- [ ] Verify clone/run instructions on a fresh checkout.
- [ ] Record incomplete morning work with an owner, rather than hiding it.

## Update protocol

Each owner writes their personal log and updates their row when starting/completing a card or encountering a blocker. Lead updates the consolidated log, shared base commit, README, and requirement statuses after integration. Before editing this shared handoff file, pull latest changes; keep edits to your row when possible.

