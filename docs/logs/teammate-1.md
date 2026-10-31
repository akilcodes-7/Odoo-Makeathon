# Teammate 1 contribution log

Role: discounts and quotation templates. Branch target: feature/offers. Available after 13:00 IST.

Actual contributor name/GitHub handle: not recorded for this implementation agent; no contributor identity is attributed.

Entry format: IST timestamp; card; what changed/why; files; checks/results; commit/PR; generated-code understanding/adaptation; blocker; next action.

## Entries

- **2026-10-31 11:12 IST — T1A discounts.** Implemented period-start eligibility with inclusive date boundaries, product/subscription scope, both minimums, deterministic highest-saving selection with ID tie-break, integer paise fixed allocation by largest remainder, and per-line percentage rounding. Added guarded `F()` usage reservation and admin-only discount create/list/detail/edit/archive screens. Existing invoice values remain in billing-created redemption and line snapshots. Files: `offers/services/discounts.py`, `offers/forms.py`, `offers/views.py`, `offers/urls.py`, `templates/offers/discount_{list,form,detail}.html`, `static/css/offers.css`, `tests/test_discounts.py`. Checks: `manage.py test tests.test_discounts tests.test_billing` — 18 tests passed; `manage.py check` — no issues; `git diff --check` on owned files — passed. Invoice reconciliation exercised: ₹250.00 subtotal − ₹10.00 discount + ₹0.00 tax = ₹240.00 total. No screenshot captured and no commit/PR created by this agent. No change to shared service signatures, models, or migrations. Next: T1B quotation templates, subject to the lead's integration and deadline; screenshot evidence remains for final review.

- **2026-10-31 11:23 IST — T1B templates and concurrency integration.** Lead added admin template create/list/detail/edit, staff read/use permissions, plan/primary/quantity/variant validation, independent subscription-line/tax copying, optional picker during draft creation, and validity copied when a quotation is issued. Files: `offers/services/templates.py`, `offers/template_forms.py`, `offers/template_views.py`, `offers/template_urls.py`, `templates/offers/template_*.html`, `subscriptions/forms.py`, `subscriptions/views.py`, `offers/urls.py`, `tests/test_templates.py`. Checks: `tests.test_templates` — 6 passed; subscription view tests — 4 passed; on-disk concurrent discount capacity check — passed (one redemption for max_uses=1). Full suite: 92 discovered, passed with 3 on-disk concurrency tests skipped in memory mode. No human Git identity/commit/PR attributed. No template screenshot captured. T1A/T1B implementation is integrated locally; final Git integration remains pending.

