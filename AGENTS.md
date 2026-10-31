# Instructions for contributors and implementation agents

## Current task boundary

This repository begins as a plan. Implement code only when the user assigns implementation work. Do not describe planned features as working. Do not create a remote repository, publish, or submit on behalf of the user without authorization and an identified destination.

## Work in small, bounded tasks

Read `docs/DEADLINES.md` before starting a card. Its hard deadlines override earlier schedule estimates. Stop implementation at 17:00 IST on 2026-10-31, including code fixes, merges, and code pushes. After the cutoff, assist only with the frozen-build demonstration and submission work authorized by the user; do not infer permission to alter submitted code.

1. Read this file, `docs/TEAM_HANDOFF.md`, and the single assigned card in `docs/TASK_CARDS.md`.
2. Read only the build-spec sections and existing files needed for that card. Do not reread every document for each small task.
3. Keep the chosen stack and contracts. Do not introduce React, FastAPI, Node tooling, Redis, Celery, cloud services, or new frameworks without a task requiring them.
4. Use the card's file ownership. Changes to shared models, migrations, root URLs/settings, common CSS/JS, or service signatures require coordination with the lead; do not silently change them.
5. Implement the complete card, run its focused checks, and record actual outcomes. Ask about a genuine blocking conflict; resolve routine details using the written defaults.
6. Update your task status and documentation entry. Summarize changed files, checks, unresolved issues, and the next dependency. Never invent test results, timings, commits, or feature completion.

## Invariants

- All financial storage uses integer paise; Decimal for rates, ratios, and conversions; no float money.
- All mutations use POST plus CSRF, server-side authorization, scoped querysets, and server-side validation.
- Subscription/invoice transitions go through `core/services/lifecycle.py`; do not write status fields directly in views, admin actions, signals, or teammate services.
- Billing uniqueness, invoice creation, discount redemption, and advancement of the billing cursor belong in one transaction per invoice period.
- Snapshot invoice amounts and billing identity. Never rebuild historical invoice values from current products, taxes, discounts, or customer profiles.
- A hidden menu does not enforce permission. Check every object and endpoint.
- Serve all fonts/icons/styles/scripts locally. Support reduced motion and keyboard interaction.
- No destructive seed defaults, committed database files, real credentials, or accidental customer-data exposure.
- Preserve other contributors' changes. Do not reset branches or rewrite shared Git history.
- Do not spawn agents unless the user explicitly requests delegation. A mention of using Luna or another model is not itself a request to spawn one.

## Documentation during the hackathon

For each completed card or meaningful blocker, add one timestamped entry to the contributor's own log under `docs/logs/`, and update their row in `docs/TEAM_HANDOFF.md`. The lead maintains the consolidated `docs/HACKATHON_LOG.md`. Every PR includes implementation summary, checks, and any change to assumptions. Use actual Asia/Kolkata timestamps; do not backdate work to fit the proposed schedule.

## Completion response

Return: card ID, implemented behavior, files changed, checks and their actual results, known limitations, and next step. Keep responses short. A card is not complete merely because its screen renders.

