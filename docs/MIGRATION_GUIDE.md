# Odoo 19 → Odoo 20 core-artifact migration guide

**Scope:** reusable guidance for custom Odoo modules and their data when moving from Odoo 19 to Odoo 20.

**Status:** a static migration guide. It describes artifact differences and verification gates; it is not a
claim that any particular module is already compatible.

## 1. What changes in a core-artifact migration

An Odoo migration is not only a Python version change. It changes the contracts between source code, the
registry, PostgreSQL metadata, XML/data records, assets, and the browser. A file may still parse while its
model, view, report, or frontend meaning has changed.

Use [`CORE_ARTIFACTS.md`](CORE_ARTIFACTS.md) as the main Odoo 19 versus Odoo 20 report. It records the
observed artifact transition, its implication, and the proof that should be collected. Use
[`MIGRATION_PROBLEMS.md`](MIGRATION_PROBLEMS.md) for symptoms and solutions from the executed migration
experience, and [`BEFORE_AFTER_EXAMPLES.md`](BEFORE_AFTER_EXAMPLES.md) when a concrete source/target snippet
is needed.

The migration must answer four separate questions:

1. Does the source load in the Odoo 20 registry?
2. Does the database contain the intended columns, constraints, indexes, XML IDs, and ownership?
3. Does the browser execute the migrated views, Owl components, reports, and POS flows?
4. Do representative business results still match the Odoo 19 reference?

A positive answer to the first question never proves the other three.

## 2. Boundaries and evidence

Work with an isolated Odoo 20 code/config/PostgreSQL/filestore stack. The source database is evidence, not a
working target. Make a raw backup and a sanitized working copy; hash both before editing or transforming.

Use placeholders in commands and notes:

```text
$ODOO19_ROOT      pinned Odoo 19 source and addons
$ODOO20_ROOT      pinned Odoo 20 source and addons
$ODOO20_SRC       Odoo 20 source tree used by static checkers
$ODOO20_CONFIG    isolated Odoo 20 configuration
$ODOO20_DB        disposable migrated database
$ODOO20_HTTP      disposable Odoo 20 HTTP base URL
```

Record the Odoo revisions, Enterprise/addon revisions, PostgreSQL version, Python environment, database
locale, installed modules, filestore hash, and backup hash. If a fact was inferred from a source diff rather
than executed, label it as an assessment until a target-side check proves it.

## 3. Inventory before editing

Build one inventory covering the following artifact classes:

| Class | Inventory items |
|---|---|
| Python/ORM | models, fields, computes, constraints, SQL views, imports, decorators, cache calls |
| Database | tables, columns, indexes, constraints, sequences, foreign keys, triggers, filestore references |
| XML/data | XML IDs, records, noupdate data, report definitions, actions, menus, translations |
| Security | models, access rows, groups, record rules, implied groups, test users |
| Views/QWeb | inherited views, modifiers, list/kanban templates, reports, mail and portal templates |
| Frontend | Owl components, services, registries, patches, assets, POS code, browser tests |
| Integrations | HTTP routes, external calls, scheduled jobs, credentials, queues, retry behavior |

For each item record source owner, target owner, disposition, dependency, migration action, and proof. A
module rename is not enough: models, tables, XML IDs, security, assets, and data may have different owners.
Use [`MIGRATION_MAPPINGS.md`](MIGRATION_MAPPINGS.md) for the mapping fields and disposition rules.
Use [`REAL_CODE_COMPARISON.md`](REAL_CODE_COMPARISON.md) when a mapping needs source evidence and a
browser/database effect, rather than relying on a textual replacement.

## 4. Odoo 19 → Odoo 20 artifact work

### 4.1 ORM and PostgreSQL metadata

Review legacy `_sql_constraints`, `_table_query`, field indexes, renamed models, removed fields, related
fields, computed fields, and all direct SQL. The important transitions include:

- legacy `_sql_constraints` declarations should be converted to `models.Constraint`; current Odoo 19 and
  Odoo 20 both warn against the old declaration, so treat this as debt discovered during migration rather
  than a new Odoo 20-only release mapping; confirm the real constraint in `pg_constraint`;
- `_table_query` report models become the Odoo 20 SQL/query form; verify every selected column and alias;
- field index metadata uses current index values rather than the old boolean-string representation;
- removed or renamed models require explicit table, relation, metadata, and XML-ID treatment;
- a field that is absent from the target registry must be redesigned, redeclared locally only when justified, or
  removed with an approved data disposition.

Do not accept a clean registry as proof that a constraint exists. Query the target schema and test duplicate
data where the constraint matters.

### 4.2 XML IDs, data, access, and record rules

Odoo 20 may move a record to another module, rename an XML ID, tighten uniqueness, or represent access and
record-rule behavior differently. The target security data uses `ir.access` rows with `operation` and an
optional `domain`; map the effective behavior rather than copying old ACL columns. For each affected record:

1. identify the old XML ID and database row;
2. identify the unique target definition, if one exists;
3. map by stable business identity, not by text similarity;
4. migrate or relink the row idempotently;
5. prove ownership, permissions, and cardinality after loading.

Treat `ir.model.access` → `ir.access`, grouped/global rule semantics, standard report rows, and moved
reference data as data migrations. Remove stale standard-owned records only after checking foreign keys and
custom ownership. Never delete ambiguous records automatically.

### 4.3 Views, QWeb, and reports

Convert old view contracts before installation, but classify each hit by the parser that consumes it:

- server-view `attrs=` and `states=` may need inline Python expressions;
- legacy server-view `<tree>` may need `<list>`;
- do not mechanically convert `attrs=` in Owl HTML or claim `<tree>` is a universal Odoo 19→20 change;
- `kanban-box` becomes `card` where required;
- `t-esc` and `t-raw` become the current escaping/output form;
- stale inherited views are classified as keep, park, recreate, or remove;
- report lines, expressions, columns, formulas, and uniqueness are checked against Odoo 20 definitions.

Validate the complete inherited view tree on a clean database and again after the migrated database is
restored. A view that loads can still be functionally wrong, so open the affected form, list, kanban, report,
mail, and portal screens in a browser.

### 4.4 Owl, account reports, POS, and assets

Rebase frontend code on the Odoo 20 owner class and current vendored Owl APIs. Do not repair an old widget by
changing only import paths. Review component props, state, refs, effects, slots, registries, services,
template inheritance, and lifecycle hooks.

For account reports and POS, test the actual lifecycle: loading, filtering, saving, offline behavior, retry,
duplicate prevention, multiple orders, and error recovery. For assets, rebuild the bundle declaration from the
target source, load with asset debugging, and run a clean browser session.

Map icons only to glyphs shipped by the target build. Run browser tests for every screen touched by an icon,
template, registry, or component change. QUnit tests may need conversion to the current Hoot runner and test
bundle.

### 4.5 Binary values, attachments, and configuration

Review every upload, export, controller, report, and attachment access. Odoo 20 binary APIs may expose raw
bytes or a `BinaryValue` wrapper where Odoo 19 code assumed a base64 string. Prove bytes, encoding, filename,
content type, RPC behavior, download behavior, and filestore presence independently.

Replace untyped configuration access with the typed `get_*`/`set_*` method that matches the business value.
Audit defaults, XML data, cache invalidation, and deployment configuration together; a correct source change
can still fail when the live service loads a different config or addons path.

## 5. Static-first migration phases

### Phase 0 — freeze and baseline

Pin source revisions, take and hash the database/filestore pair, record module and schema totals, and choose
the disposable Odoo 20 stack. Do not begin by testing on production or by repeatedly installing until the
next traceback appears.

### Phase 1 — static inventory

Run the read-only scanners in `scripts/`, classify each hit, and assign a target proof. Check official Odoo
20 upgrade helpers before writing a bespoke transform. Review every generated diff; official scripts may only
transform the first occurrence or one side of a relationship.

### Phase 2 — code and metadata port

Update the manifest target version first. Port ORM declarations, imports, constraints, SQL/query models, XML
IDs, access data, views, QWeb, assets, and frontend code in dependency order. Keep the source module name
stable when the database upgrade depends on it; a repository/container name is a separate choice.

### Phase 3 — empty-database gates

Install from an empty Odoo 20 database. Require a clean registry, expected module state, no undefined columns,
and no unexplained traceback. Verify the target schema, constraints, XML IDs, access rows, and assets before
restoring migrated data.

### Phase 4 — migrated-database gates

Restore only a copy into the isolated Odoo 20 cluster. Run supported pre-migration transformations, upgrade
the target modules, and inspect schema and data. Repeat on a fresh copy until the process is deterministic.

### Phase 5 — functional and browser gates

Run Python and frontend tests, then exercise representative accounting, sales, stock, HR, payroll, POS,
reporting, portal, mail, attachment, and integration workflows that exist in the source scope. Compare
expected totals and record counts with the frozen Odoo 19 baseline.

### Phase 6 — release evidence

Prove backup and restore, access with non-administrator users, scheduled actions, queues, performance smoke,
logs, rollback, and the exact code/config/database/filestore revisions. Production consideration requires an
approved rehearsal and an explicit release decision.

## 6. Verification commands

Adapt these examples to the isolated environment and protected secret handling:

```bash
python3 scripts/check_imports20.py --root "$ODOO20_SRC"
python3 scripts/check_registry_env20.py --root "$ODOO20_SRC"
bash scripts/static_audit20.sh "$ODOO20_ROOT"

"$ODOO20_ROOT/odoo-bin" -c "$ODOO20_CONFIG" -d "$ODOO20_DB" \
  -u <module_list> --stop-after-init
```

After every model or field change, inspect `information_schema.columns`, `pg_constraint`, indexes, module
states, XML IDs, and representative row counts. The exact SQL belongs in the project runbook because table
names and business invariants vary.

Use [`STATIC_FIRST_PROCEDURE.md`](STATIC_FIRST_PROCEDURE.md) for the scanner sequence and the script-specific
gates. Use [`QUICK_REFERENCE.md`](QUICK_REFERENCE.md) when diagnosing a known symptom.

## 7. Definition of done

A migration is ready for release review only when all of the following are true:

- the module and dependency inventory has an owner and disposition for every item;
- source, target, database, filestore, and configuration revisions are recorded;
- empty-database installation and migrated-database upgrade both pass;
- target columns, indexes, constraints, XML IDs, access rules, and record counts are proven;
- no removed API, stale view, missing module, missing attachment, or unexplained log error remains;
- browser and business workflows pass with representative non-admin users;
- accounting, stock, HR/payroll, POS, report, integration, and backup results are reconciled where applicable;
- rollback and restore have been rehearsed;
- the final review records known limitations, deferred modules, and explicit approval.

The final deliverable is evidence-backed compatibility, not merely a successful command or a clean startup
log.
