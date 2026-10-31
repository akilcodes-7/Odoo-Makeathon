# Brightloop — Subscription Management System

Hackathon project for managing products, recurring plans, quotations, subscriptions, invoices, discounts, payments, and customer self-service.

**Current status: S0 foundation complete.** The project boots, its full initial schema migrates, demo roles seed idempotently, and navigation renders honest placeholder screens. S1 authentication, the catalog and all subscription, billing, discount, payment, reporting, and portal features have not been implemented. See the live [handoff](docs/TEAM_HANDOFF.md) and [progress log](docs/HACKATHON_LOG.md).

## Start here

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
- Each teammate uses their own Git identity, feature branch, meaningful commits, and PR reviews. Do not manufacture contributions or backdate activity.
- Planned times are not actual completion timestamps. Actual progress belongs in the [hackathon log](docs/HACKATHON_LOG.md).
- Akilan is the provisional portal submitter; repository owner handles evaluator access. The 17:00–17:30 period is for the frozen-build video and submission, not additional coding.

## Run the S0 preview

Verified with Python 3.12.14 and Django 5.2.18. Create a virtual environment, install the pinned requirement, migrate and run the placeholder UI:

```text
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

`python manage.py seed_demo` creates local demo users for the three roles. Choose one shared local-only password when prompted; it must have at least nine characters, uppercase and lowercase letters, and a special character. The command does not print or reset passwords. Its emails are `admin@brightloop.test`, `staff@brightloop.test`, and `customer@brightloop.test`.

**Current preview limitation:** feature URLs intentionally show “Not implemented yet” placeholders. Demo accounts do not enable application login until S1. Billing, scale-seed, benchmark, payment, and feature test commands are planned but do not exist yet. Do not imply the preview is the finished subscription system.

## Evaluation evidence

All completion claims should link to actual commits, PRs, screenshots, or captured check results. Initial S0 verification results are in [the hackathon log](docs/HACKATHON_LOG.md); feature requirements still pending are tracked in [requirements](docs/REQUIREMENTS.md). Local seed accounts are demonstration accounts; actual email delivery, concurrency, and performance must be described according to what was actually verified.

## Source material

- User-provided `Subscription_Management_System.pdf`, four pages.
- [Hackathon portal](https://hackathon.odoo.com/hackathon/details/79054). The portal requires authentication; its must-have and nice-to-have lists were supplied directly by the participant and are recorded in [requirements](docs/REQUIREMENTS.md).
- Participant-provided solo/team schedule and subsequent implementation decisions.

