# Odoo 19 → 20 Migration Skill and Problem-Solving Playbook

This repository packages a reusable Claude/Codex skill for migrating custom Odoo 19 modules to Odoo 20.
It combines:

- the complete migration skill used during a real multi-module port;
- a quick-reference catalog of migration failures, symptoms, and solutions;
- a public report of Odoo core artifact changes between Odoo 19 and Odoo 20;
- explicit database, XML-ID, model, API, frontend, and module-taxonomy mappings;
- a static-first procedure and reusable audit/migration scripts.

The material is intentionally public-safe. It contains no database dumps, credentials, private keys,
customer data, filestore contents, or deployment secrets. Replace the example paths and database names
with values from your own controlled environment.

## Start here

1. Read [`SKILL.md`](SKILL.md).
2. Read [`docs/MIGRATION_PROBLEMS.md`](docs/MIGRATION_PROBLEMS.md) for the observed failure catalog.
3. Read [`docs/CORE_ARTIFACTS.md`](docs/CORE_ARTIFACTS.md) for the Odoo 19 → 20 artifact implications.
4. Read [`docs/MIGRATION_MAPPINGS.md`](docs/MIGRATION_MAPPINGS.md) before changing models or data.
5. Follow [`docs/STATIC_FIRST_PROCEDURE.md`](docs/STATIC_FIRST_PROCEDURE.md).
6. Run the read-only scanners before the first Odoo 20 install attempt.

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

The documentation is offered for community reuse. Choose and add a project license before publishing
the repository; the original Odoo modules, Enterprise code, OCA code, and customer-specific code retain
their own licenses.
