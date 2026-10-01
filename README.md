# Odoo 19 → 20 Migration Skill and Problem-Solving Playbook

This repository packages a reusable Claude/Codex skill for migrating custom Odoo 19 modules to Odoo 20.
It combines:

- the complete migration skill used during a real multi-module port;
- a quick-reference catalog of migration failures, symptoms, and solutions;
- a public report of Odoo core artifact changes between Odoo 19 and Odoo 20;
- side-by-side Odoo 19 → 20 code and XML examples;
- explicit database, XML-ID, model, API, frontend, and module-taxonomy mappings;
- a static-first procedure and reusable audit/migration scripts.

The material is intentionally public-safe. It contains no database dumps, credentials, private keys,
customer data, filestore contents, or deployment secrets. Replace the example paths and database names
with values from your own controlled environment.

## Start here

1. Read [`SKILL.md`](SKILL.md).
2. Read [`docs/MIGRATION_PROBLEMS.md`](docs/MIGRATION_PROBLEMS.md) for the observed failure catalog.
3. Read [`docs/CORE_ARTIFACTS.md`](docs/CORE_ARTIFACTS.md) for the Odoo 19 → 20 artifact implications.
4. Read [`docs/BEFORE_AFTER_EXAMPLES.md`](docs/BEFORE_AFTER_EXAMPLES.md) for concrete code and XML changes.
5. Read [`docs/REAL_CODE_COMPARISON.md`](docs/REAL_CODE_COMPARISON.md) for source-anchored Odoo 19 → 20
   code, runtime, database, and browser effects.
6. Read [`docs/MIGRATION_MAPPINGS.md`](docs/MIGRATION_MAPPINGS.md) before changing models or data.
7. Follow [`docs/STATIC_FIRST_PROCEDURE.md`](docs/STATIC_FIRST_PROCEDURE.md).
8. Run the read-only scanners before the first Odoo 20 install attempt.

The core-artifact report is intentionally limited to reusable Odoo 19 → 20 technical changes. Project- or
customer-specific implementation names are excluded from the public report for data protection.

## Non-negotiable safety rules

- Migrate a copy, never the source database in place.
- Freeze and hash the database dump and filestore before editing anything.
- Use a dedicated Odoo 20 code/config/PostgreSQL stack.
- Perform static inventory before install-crash iteration.
- Verify columns and database constraints after every schema change.
- Treat a clean registry as a technical milestone, not functional acceptance.
- Test browser behavior, access rights, accounting, stock, HR/payroll, POS, backup, and rollback.
- Never commit credentials, private keys, customer exports, or raw migration logs.

## Scope and license

The original documentation and scripts in this repository are released under the [MIT License](LICENSE).
That license does not relicense Odoo, Odoo Enterprise, OCA, or customer-specific code copied into a user's
own migration workspace; those components retain their own licenses and copyright notices.
