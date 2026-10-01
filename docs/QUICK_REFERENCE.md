# Quick reference

## Before coding

```text
freeze source + target revisions
select reference by business scope
backup database + filestore
hash both artifacts
restore raw copy and sanitized working copy
inventory manifests, dependencies, installed modules
run static scan and classify every hit
```

## Before first Odoo 20 start

```text
use a separate Odoo 20 code/config/PostgreSQL stack
normalize indexes and known core data changes
prepare ir.access conversion
prepare stale-view/report cleanup
build the missing-module disposition matrix
```

## After every model/data change

```text
targeted module upgrade
Modules loaded / Registry loaded
no UndefinedColumn or critical errors
information_schema.columns check
pg_constraint check
ir_module_module version/state check
```

## Before release

```text
clean install
populated-database upgrade
accounting/tax reconciliation
sales/stock workflow
HR/payroll workflow
POS/offline/retry workflow
browser actions and console
non-admin security
attachments/filestore
performance smoke
backup/restore
rollback rehearsal
written acceptance
```

## What not to claim

- “The module is migrated” from a clean registry alone.
- “The database is clean” while Odoo 19-only modules remain without disposition.
- “The browser works” from an HTTP 200 response.
- “The constraint exists” because Odoo logged only a warning.
- “The upgrade used the right code” without checking the live service addons path.
