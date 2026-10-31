# Brightloop evaluator walkthrough

## Start and sign in

Prerequisites: Git, Python 3.12+ with venv/pip support, and internet for the first dependency installation.

```bash
git clone --branch Main https://github.com/akilcodes-7/Odoo-Makeathon.git
cd Odoo-Makeathon
python3 scripts/run_demo.py
```

Windows: replace the last command with `py -3.12 scripts/run_demo.py`. If the port is busy, append `--port 8001` and use that port in the browser. Open the HTTP URL printed by the command, not a template HTML file.

The launcher creates a separate persistent SQLite database in `.demo/`. It generates one installation-specific password, stored privately in `.demo/access.txt`, for these accounts:

| Account | Role |
| --- | --- |
| `admin@brightloop.test` | Manage products, plans, taxes, discounts, quotation templates, staff and business operations |
| `staff@brightloop.test` | Manage customers, quotes, subscriptions, invoices and payments |
| `customer@brightloop.test` | Acme customer portal; own subscriptions, invoices and profile |
| `customer2@brightloop.test` | Globex customer portal; separate records for isolation checks |

Use the password from `.demo/access.txt`. To supply your own password, set `BRIGHTLOOP_DEMO_PASSWORD` before the **first** launch. Subsequent launches reuse the existing accounts and data. Stop the server with Ctrl+C; restart using the same command. These local files are ignored by Git; no database or credentials are shipped in the repository.

## Complete a real workflow

1. **Staff:** Sign in and open **Subscriptions → EVAL-READY**. Review its customer, monthly plan, prices and tax. Issue the quotation, confirm it, then activate it. Each transition is saved with an event.
2. **Billing:** Open **Invoices → Run billing**. Find the invoice belonging to `EVAL-READY`. Run billing again: it must not create another invoice for the same period. `EVAL-BILLING` separately demonstrates automatic activation of a confirmed contract whose start is today.
3. **Invoice:** Open the generated draft and confirm it. View its saved subtotal, discount, tax, total and balance. Send the invoice; its email is saved under `.demo/emails/`. Print opens the saved invoice layout.
4. **Payment:** On the confirmed invoice, record a payment smaller than its balance, using today's date. The invoice stays confirmed with a reduced balance. Record the remaining balance: it becomes **Paid**. Payments are recorded demonstrations, with no gateway charge. The Payments page links back to invoices for recording another payment.
5. **Customer:** Sign out and sign in as `customer@brightloop.test`. The portal shows this customer's invoice, payments and subscription. Sign in as the second customer and try the first customer's invoice URL: access is denied.

## Other working examples

| Example | What to try |
| --- | --- |
| `EVAL-PARTIAL` | A confirmed, partially paid invoice with an outstanding balance; complete payment from its invoice page |
| `EVAL-RENEW` | As the second customer, request renewal during the final period; one successor draft is created for staff review, starting after the current term |
| `EVAL-PAUSE` | As the first customer, inspect the scheduled pause and resume; staff/customer actions honor the plan flags |
| Base demo records | Daily, weekly, monthly and annual plans; draft, quotation, future confirmed, active and closed contracts; taxes, discounts, variants and a reusable quote template |

**New accounts:** Sign out and choose **Create a customer account** on the login screen. Signup creates a customer login and profile; staff can select that customer when creating a subscription. Under **Team accounts**, an admin can create a staff login. Creating an internal customer from the Customers page alone does not create a login or automatically claim an existing account.

**Create your own sale:** Admin configures a product/plan/tax under Products & plans. Staff opens New draft, selects a customer and plan, adds exactly one primary line (or selects the matching quotation template), supplies dates and saves. Continue the workflow above. The Standard SaaS Onboarding template belongs to Professional Monthly.

## Scope and verification

This is a locally runnable, database-backed application. Billing runs from the UI or management command; there is no background scheduler. Invoice and password-reset emails are generated as local files for this evaluator setup, with no external mail delivery. Password reset links can be opened from those files. Payments are recorded manually; live gateways, refunds and credit notes are outside the current scope. Synthetic demo data contains no real customer records.

The automated evaluator workflow exercises real login and mutation forms with CSRF enabled, billing idempotency, partial/full settlement, email generation, customer isolation, new accounts and renewal/resume. Run it with:

```bash
.venv/bin/python manage.py test tests.test_evaluation_workflow
```

On Windows use `.venv\Scripts\python.exe`. Tests use a separate test database. Browser/viewport checks and full test results are recorded in the contributor log; historical audit entries are tied to their stated commits and dates.
