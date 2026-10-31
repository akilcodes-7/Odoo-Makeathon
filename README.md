# Brightloop — Subscription Management System

A Django application for managing products, recurring plans, subscriptions, invoices, discounts, payments, and a customer self-service portal.

---

## Quick start

For evaluators, install Python 3.12+ and Git, then run:

```bash
git clone --branch Main https://github.com/akilcodes-7/Odoo-Makeathon.git
cd Odoo-Makeathon
python3 scripts/run_demo.py
```

On Windows, use `py -3.12 scripts/run_demo.py`. This command installs dependencies, migrates a separate `.demo/db.sqlite3`, creates four working accounts and a populated evaluation dataset, then starts the app at **http://127.0.0.1:8000/**. Internet is required for the first dependency installation. Read **`.demo/access.txt`** for the generated sign-in password. Rerunning the command preserves your records and passwords. Use `--port 8001` if port 8000 is busy; `--prepare-only` prepares data without starting a server.

Follow [the evaluator walkthrough](docs/EVALUATOR_GUIDE.md) for a complete quote-to-payment demo, customer signup, staff accounts, renewal and pause/resume. Email is written to `.demo/emails/` for inspection; no messages or payments are sent externally. `.demo/` is excluded from Git.

### Manual developer setup

```bash
git clone --branch Main https://github.com/akilcodes-7/Odoo-Makeathon.git
cd Odoo-Makeathon
python3.12 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo         # creates admin / staff / customer accounts
python manage.py runserver
```

Open **http://127.0.0.1:8000** and log in with one of the demo accounts below.

> **`seed_demo` prompts for one shared password** (min 9 chars, upper + lower + special).
> It never prints or resets an existing password.

---

## Demo accounts & credentials

The evaluator launcher generates a local password in `.demo/access.txt`. With the manual setup instead, `seed_demo` asks you to choose the password. Both setups use the account emails below; no shared password is shipped in the repository.

| Role       | Email                        | Organization / Name          |
|------------|------------------------------|------------------------------|
| Admin      | `admin@brightloop.test`      | Demo Admin (superuser)       |
| Staff      | `staff@brightloop.test`      | Demo Staff                   |
| Customer 1 | `customer@brightloop.test`   | Acme Technologies Pvt Ltd    |
| Customer 2 | `customer2@brightloop.test`  | Globex Corporation India     |

> Re-running `seed_demo` leaves existing passwords unchanged. To reset local demo passwords, run `python manage.py seed_demo --reset-passwords`; it prompts for a new password unless `BRIGHTLOOP_DEMO_PASSWORD` is set in your environment.

---

## Key URLs

| Area                  | URL                          | Who can access         |
|-----------------------|------------------------------|------------------------|
| Home / login          | `/`                          | Everyone               |
| Catalog               | `/catalog/`                  | Admin, Staff           |
| Subscriptions         | `/subscriptions/`            | Admin, Staff           |
| Customers             | `/customers/`                | Admin, Staff           |
| Discounts & Templates | `/offers/`                   | Admin, Staff           |
| Billing               | `/billing/`                  | Admin, Staff           |
| Invoices              | `/invoices/`                 | Admin, Staff           |
| Payments              | `/invoices/payments/`        | Admin, Staff           |
| Dashboard (API)       | `/api/dashboard/summary/`    | Admin, Staff           |
| Customer portal       | `/portal/`                   | Customer               |

---

## Repo layout

```
.
├── accounts/           # Custom user model, roles, password reset
├── catalog/            # Products, variants, plans, taxes
├── core/
│   ├── models/         # All domain models
│   ├── services/
│   │   ├── lifecycle.py  # ONLY place that writes subscription/invoice status
│   │   ├── billing.py    # Recurring invoice creation & batch billing
│   │   ├── finance.py    # Balance queries
│   │   ├── pricing.py    # Period, line, and tax calculation types
│   │   └── dates.py      # Period arithmetic
│   └── management/commands/
│       ├── seed_demo.py       # Create demo accounts & data
│       ├── seed_scale.py      # Create 5 000-subscription benchmark dataset
│       └── run_billing.py     # Trigger billing from the command line
├── offers/             # Discounts and quote templates
├── subscriptions/      # Subscription views and forms
├── portal/             # Customer-facing portal
├── insights/           # Dashboard and MRR reporting
├── finance/            # Invoice and payment views
├── tests/              # Full test suite
├── static/             # CSS and JS (served locally; no CDN)
├── templates/          # Django HTML templates
├── manage.py
└── requirements.txt
```

---

## Running tests

```bash
# Full suite (in-memory SQLite)
python manage.py test --verbosity 1

# Concurrent-write tests (requires on-disk DB)
TEST_DATABASE_PATH=/tmp/brightloop-test.sqlite3 python manage.py test tests.test_concurrency
```

---

## Billing

Billing is triggered manually — there is no background scheduler.

```bash
# Bill everything due as of today
python manage.py run_billing

# Simulate a future date (demo / testing only)
python manage.py run_billing --as-of 2026-11-30
```

Staff can also click **Run billing** in the `/billing/` UI.

---

## Email

Email defaults to Django's **console backend** — messages print to the terminal.
For real delivery, set these environment variables before starting the server:

```bash
export EMAIL_HOST=smtp.example.com
export EMAIL_PORT=587
export EMAIL_HOST_USER=you@example.com
export EMAIL_HOST_PASSWORD=secret
export EMAIL_USE_TLS=true
export EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
```

Without `EMAIL_BACKEND`, Django uses the console backend and prints messages to the terminal.

---

## Performance dataset (optional)

```bash
python manage.py seed_scale --subscriptions 5000
python manage.py benchmark_pages --warm-samples 10
```

---

## Stack

| Layer        | Choice                                      |
|--------------|---------------------------------------------|
| Language     | Python 3.12                                 |
| Framework    | Django 5.2.18                               |
| Database     | SQLite (local dev)                          |
| Templates    | Django HTML templates                       |
| Styles/JS    | Plain CSS + vanilla JS (all local, no CDN)  |
| Money        | Integer paise storage, `Decimal` arithmetic |
| Currency     | INR only                                    |

---

## Core design rules

- **Lifecycle transitions** go only through `core/services/lifecycle.py`. Never write `.status` directly.
- **Money** is stored as integer paise. Use `Decimal` for calculations. No floats.
- **Invoice snapshots** are immutable — historical amounts never rebuild from current catalog data.
- **Permissions** are server-enforced on every object and endpoint, not just in the nav.
- **POST + CSRF** required for all mutations.

---

## docs/ reference

| File | Purpose |
|------|---------|
| `docs/AUDIT_2026-10-31.md` | Functional audit — 10 reproduced defects with exact triggers |
| `docs/REPAIR_AND_UI_REDESIGN_PLAN.md` | Phase-by-phase repair and redesign plan |
| `docs/TEAM_HANDOFF.md` | Branch, commit, and owner board |
| `docs/DEADLINES.md` | Hard submission deadlines |
| `docs/REQUIREMENTS.md` | Requirement coverage evidence |
| `docs/DEMO_AND_CHECKS.md` | Demo script and verification checklist |
| `docs/HACKATHON_LOG.md` | Consolidated progress log |
