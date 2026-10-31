# Brightloop — Subscription Management System

Hackathon project for managing products, recurring plans, quotations, subscriptions, invoices, discounts, payments, and customer self-service.

**Current status: core features exist, but functional acceptance is incomplete.** The [31 October functional audit](docs/AUDIT_2026-10-31.md) reproduced ten defects, including blocked product creation, tax and money-form corruption, and a stale draft edit that can undo confirmation. The existing suite discovers 96 tests: 93 pass and three concurrency cases skip in the default database; those three pass separately on disk. Earlier backend performance measurements passed, but they do not establish complete functionality. Exact viewport checks, browser timing and human Git participation evidence remain incomplete. See the audit for the repair order, plus [requirements](docs/REQUIREMENTS.md), [demo/check evidence](docs/DEMO_AND_CHECKS.md), the [handoff](docs/TEAM_HANDOFF.md), and [progress log](docs/HACKATHON_LOG.md).

## Start here

**Shared team branch: `dev` (lowercase).** All current implementation, audit findings and the single [repair and UI redesign plan](docs/REPAIR_AND_UI_REDESIGN_PLAN.md) are handed off through this branch. Repairs and the redesign are still planned. Start with the plan and [current handoff](docs/TEAM_HANDOFF.md).

Clone the team branch explicitly because the repository's default branch is different:

```text
git clone --branch dev https://github.com/akilcodes-7/Odoo-Makeathon.git
cd Odoo-Makeathon
```

| Reader | Read first |
| --- | --- |
| Evaluator | This README, [requirement coverage](docs/REQUIREMENTS.md), then [progress log](docs/HACKATHON_LOG.md) |
| Developer implementing a task | [Agent instructions](AGENTS.md), [task cards](docs/TASK_CARDS.md), and the referenced section of the [build specification](docs/IMPLEMENTATION_PLAN.md) |
| Teammate joining at 1 pm | [team handoff](docs/TEAM_HANDOFF.md), then your task card |
| Person preparing the demonstration | [demo and verification checklist](docs/DEMO_AND_CHECKS.md) |

## Stack decision

- Python 3.12; Django 5.2.18 pinned in requirements.txt.
- SQLite for a local database; Django ORM and migrations.
- Django templates and forms, custom local CSS, and small vanilla JavaScript enhancements.
- Django sessions, a custom email-based user model, server-enforced roles, and Django password-reset tokens.
- Local email output by default; environment-configured SMTP for actual delivery when available.
- Integer paise in storage and Decimal arithmetic for calculations; INR is the single demo currency.
- A Django management command for scheduled billing, plus an internal “Run billing” action calling the same service.

No Node build, CDN, cloud database, payment gateway, or external API is required for the core local demonstration. Initial dependency installation requires an available package source or previously cached packages.

## Scope

Core scope includes authentication, customers, products/variants, configurable plans, quotation templates, subscription lifecycle, recurring billing, taxes, discounts, invoice actions, payments, dashboards including MRR, and a customer portal. See [requirement coverage](docs/REQUIREMENTS.md) for exact definitions and evidence still needed.

The UI will use a light workspace, plum navigation, teal accents, readable financial tables, responsive forms, keyboard-visible focus, and restrained motion that respects reduced-motion preferences.

## Schedule and collaboration

**Hard deadlines, 31 October 2026 IST:** repository URL submitted at **09:00**; evaluator collaborator access by **10:00**; coding stops at **17:00**; video URL submitted by **17:30**. These are participant-supplied deadlines. See [deadline owners and status](docs/DEADLINES.md); submission permissions and actual completion remain unverified.

- **9:00 am–1:00 pm IST:** solo foundation, authentication, catalog, subscriptions, and billing spine.
- **1:00 pm–5:00 pm IST:** teammate 1 owns discounts/templates; teammate 2 payments/invoice delivery; teammate 3 dashboard/portal; lead owns integration and shared code.
- `dev` is the shared integration and handoff branch. Each teammate uses their own Git identity and isolated task branch where required by the repository workflow, then integrates completed work into `dev`. Do not manufacture contributions or backdate activity.
- Planned times are not actual completion timestamps. Actual progress belongs in the [hackathon log](docs/HACKATHON_LOG.md).
- Akilan is the provisional portal submitter; repository owner handles evaluator access. The 17:00–17:30 period is for the frozen-build video and submission, not additional coding.

## Run the local application

Verified with Python 3.12.14 and Django 5.2.18. Create a virtual environment, install the pinned requirement, migrate and run the application with the audit limitations recorded above:

```text
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
```

`seed_demo` creates local demo users for the three roles. Choose one local-only password when prompted; it must have at least nine characters, uppercase and lowercase letters, and a special character. The command does not print or reset existing passwords. Its emails are `admin@brightloop.test`, `staff@brightloop.test`, and `customer@brightloop.test`. Email defaults to the console backend; actual SMTP delivery needs environment configuration. Billing is available through the management command and staff POST action; no external scheduler or payment gateway is configured.

To create a repeat-safe local benchmark dataset, run `python manage.py seed_scale --subscriptions 5000` after `seed_demo`, then measure authenticated routes with `python manage.py benchmark_pages --warm-samples 10`. These commands write only to the configured local database. Run the full unit/integration suite with `python manage.py test`; run real concurrent-write checks against a temporary on-disk test DB with `TEST_DATABASE_PATH=/tmp/brightloop-concurrency.sqlite3 python manage.py test tests.test_concurrency`.

**Known limitations:** responsive browser screenshots at 390, 768, and 1440 px have not been captured; the 5,000-record timings measure Django request handling, not full browser rendering or concurrent load. Delivery uses the configured Django email backend; no background scheduler, live payment gateway, refunds, or credit notes are implemented. Portal submission, evaluator access, and video submission remain unverified. The pushed task branch and `dev` refs are recorded in the handoff.

## Evaluation evidence

All completion claims should link to actual commits, PRs, screenshots, or captured check results. Current results and limitations are in [the demo/check record](docs/DEMO_AND_CHECKS.md) and [requirements](docs/REQUIREMENTS.md). Implementation commit `0b436d9` and documentation commits `cee28fb`/`c9638c8` are on `codex/remaining-core` and `dev`; the fresh clone used for setup verification was from the pushed `dev`. The remote default branch remains unchanged.

## Source material

- User-provided `Subscription_Management_System.pdf`, four pages.
- [Hackathon portal](https://hackathon.odoo.com/hackathon/details/79054). The portal requires authentication; its must-have and nice-to-have lists were supplied directly by the participant and are recorded in [requirements](docs/REQUIREMENTS.md).
- Participant-provided solo/team schedule and subsequent implementation decisions.

