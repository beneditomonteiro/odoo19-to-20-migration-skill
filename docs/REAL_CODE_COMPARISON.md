# Verified Odoo 19 → Odoo 20 source comparison

This document replaces a generic “check the target source” warning with a small, reproducible comparison
of the actual Odoo 19 and Odoo 20 code that owns the migration behavior. The paths below are relative to
the corresponding Odoo source tree; they do not expose a customer project, database, or deployment path.

## Evidence baseline

The comparison was made against:

- Odoo 19 community source: `19.0`, revision `fc09561d584175028f14c71ca20855bbb4855f99`, snapshot 2026-09-20.
- Odoo 20 source: `20.0+e.20260924`, snapshot 2026-09-24. The source reports `version_info = (20, 0, 0, ...)`.

Patch releases can change signatures and implementation details. The examples below are therefore source-
anchored teaching examples, not promises that every Odoo 20 build has identical line numbers.

## At-a-glance map

| Artifact | Odoo 19 evidence | Odoo 20 superseding evidence | Status |
|---|---|---|---|
| Virtual SQL models | `odoo/orm/models.py:427-427, 488-499`; core `_table_sql` wraps `_table_query` | `odoo/orm/models.py:530-549`; core `_table_sql` resolves the model table and flush metadata; it no longer reads `_table_query` | Confirmed release change |
| Sales/report SQL | `addons/sale/report/sale_report.py:229-242`; `_query()` returns an interpolated SQL string and `_table_query` exposes it | `odoo/addons/sale/report/sale_report.py:123-128`; `Domain`, `TableSQL`, `SQL`, and `Query.subselect()` build the report relation | Confirmed source redesign |
| Model access | `odoo/addons/base/models/ir_model.py:2080+`; model name `ir.model.access`; CSV has four `perm_*` columns | `odoo/addons/base/models/ir_access.py:64-87`; model name `ir.access`; CSV uses `operation` and `domain` | Confirmed data/security change |
| Owl/QWeb migration | Legacy custom code can contain Owl 2 patterns such as `useState`, `t-esc`, and `t-slot` | `odoo/upgrade_code/owl3-migration.py:746-756, 852-890, 1259-1278`; current source uses `proxy`, `t-out`, and `t-call-slot` in affected paths | Confirmed frontend migration work |
| SQL constraints | `odoo/orm/model_classes.py:162-164` already warns that `_sql_constraints` is unsupported | `odoo/orm/model_classes.py:175-177` emits the same warning and asks for `models.Constraint` | Not a new 19→20 delta; legacy debt in both |
| `<tree>`, `attrs=`, `states=` | Some custom/legacy code may still contain them; much Odoo 19 core already uses `<list>` | Odoo 20 still contains isolated legacy occurrences; counts alone do not prove a release mapping | Not a blanket release conversion |

The last two rows matter: a migration report must distinguish a real source change from a pre-existing
legacy pattern that happens to be discovered during a port.

## 1. Virtual SQL models: `_table_query` to `_table_sql`

### Source shape in Odoo 19

The Odoo 19 base model declares `_table_query` and computes `_table_sql` from it. The test model in
`odoo/addons/test_orm/models/test_orm.py:2401-2409` uses the old contract:

```python
@property
def _table_query(self):
    return """
        SELECT tag.id AS id, SUM(child.quantity) AS sum_quantity, tag.id AS tag_id
        FROM test_orm_any_child AS child
        JOIN test_orm_any_child_test_orm_any_tag_rel AS rel
          ON rel.test_orm_any_child_id = child.id
        JOIN test_orm_any_tag AS tag ON tag.id = rel.test_orm_any_tag_id
        GROUP BY tag.id
    """
```

### Superseding shape in Odoo 20

The Odoo 20 base model no longer defines `_table_query` and its default `_table_sql` is the physical table
identifier. The corresponding Odoo 20 test model at `odoo/addons/test_base/models/test_orm.py:2280-2291`
uses an `SQL` object and carries the inherited flush metadata:

```python
@property
def _table_sql(self):
    return SQL(
        """(
        SELECT tag.id AS id, SUM(child.quantity) AS sum_quantity, tag.id AS tag_id
        FROM test_orm_any_child AS child
        JOIN test_orm_any_child_test_orm_any_tag_rel AS rel
          ON rel.test_orm_any_child_id = child.id
        JOIN test_orm_any_tag AS tag ON tag.id = rel.test_orm_any_tag_id
        GROUP BY tag.id
        )""",
        to_flush=super()._table_sql._sql_tuple[2],
    )
```

### Real effect

Leaving only `_table_query` in a custom `_auto = False` model does not preserve the Odoo 19 virtual
relation. The target can try to read the generated physical table instead, producing a missing-relation or
wrong-column error, or a report that no longer returns the expected rows. Rewriting the property is not enough:
the selected aliases, joins, dependencies, flush behavior, record rules, and report totals still need review.

### Visual and database proof

Open the report/list view and apply a filter that exercises every join. Compare row count and totals with a
fixed Odoo 19 reference. In the target database, inspect the generated query from the server log or SQL
debugging and verify every field declared on the model has a selected alias. A successful registry load alone
does not prove that the virtual relation can be queried.

## 2. Report SQL: string assembly to query objects

The Odoo 19 `sale.report` implementation at `addons/sale/report/sale_report.py:229-242` assembles a `WITH`,
`SELECT`, `FROM`, `WHERE`, and `GROUP BY` string through `_query()`. Odoo 20's corresponding implementation
at `odoo/addons/sale/report/sale_report.py:123-128` starts from an ORM `Query`, assigns a grouped `SQL` fragment,
and returns `query.subselect(...)`.

The essential target shape is:

```python
from odoo import fields
from odoo.fields import Domain
from odoo.models import TableSQL
from odoo.tools import SQL

@property
def _table_sql(self) -> SQL:
    query = self.env["sale.order.line"].sudo().with_context(date_to=fields.Date.today())._search(
        Domain("display_type", "=", False)
    )
    query.groupby = SQL(", ").join(self._groupby_list(query.table))
    return query.subselect(*self._select_dict_to_list(self._select_dict(query.table)))
```

The helper methods are part of the report implementation; do not copy this shortened example without
porting their field aliases and aggregations. The target `TableSQL` object exposes fields as SQL expressions,
which lets the query builder carry table/flush metadata and safely compose parameters.

### Real effect

A mechanical copy of a 19-style string query can fail at registry setup, lose automatic flushing before a
report read, mishandle aliases, or return different grouped totals. The failure may only appear after a user
opens a report or changes a date/company filter.

### Visual proof

Compare the report's list, pivot, graph, date filter, company filter, currency conversion, and drill-down
action. Reconcile at least one known order total and one empty-result filter. A report that opens is not enough;
the grouping and drill-down must identify the same business records.

## 3. Access data: `ir.model.access` to `ir.access`

Odoo 19's test data at `odoo/addons/test_orm/security/ir.model.access.csv` uses:

```csv
"id","name","model_id:id","group_id:id","perm_read","perm_write","perm_create","perm_unlink"
access_category,test_orm_category,test_orm.model_test_orm_category,base.group_user,1,1,1,1
```

The Odoo 20 test data at `odoo/addons/test_base/security/ir.access.csv` uses the new model and columns:

```csv
id,name,model_id,group_id/id,operation,domain
access_category,test_orm_category,test_orm.category,base.group_user,crud,
```

The target model at `odoo/addons/base/models/ir_access.py:64-87` stores `operation`, an optional `domain`,
and a computed `kind` distinguishing permission from restriction. This is why an old ACL row must not be
converted into a guessed XML record with an invented field name: use the target CSV/data schema and preserve
the effective security semantics.

### Real effect

The data controls whether a user can read, update, create, or delete records, and a domain can restrict the
records to which an operation applies. An incorrect conversion can make a screen look normal for an
administrator while exposing records to ordinary users, or can make a legitimate action fail only after a
non-admin opens it.

### Visual and security proof

Test the same menu and form as administrator, ordinary user, manager, and a user in another company. For each
role, check read, create, update, delete, related-record reads, and domain filtering. Record both an allowed
operation and a deliberately denied operation. Verify the loaded `ir.access` rows and XML IDs in the target
database; do not validate only the CSV syntax.

## 4. Owl and QWeb: source transformations with browser effects

The Odoo 20 upgrade helper itself documents the concrete transformations:

| Legacy pattern | Target/source-backed pattern | Evidence | Observable effect |
|---|---|---|---|
| `useState` imported from the compatibility path | `proxy` from `@odoo/owl` in affected current code | `upgrade_code/owl3-migration.py:746-756`; e.g. `addons/web/.../*.js` | State changes may stop re-rendering, or the browser throws an import/runtime error. |
| `t-esc="expr"` | `t-out="expr"` | `upgrade_code/owl3-migration.py:852-890` | Text, HTML, report, mail, and portal output can render differently. |
| `t-slot="name"` | `t-call-slot="name"` | `upgrade_code/owl3-migration.py:1259-1278` | A component slot can disappear or render outside the intended wrapper. |
| old refs/listener helpers | current signal/ref and listener APIs | current Owl source plus upgrade helper | Focus, autocomplete, popovers, or cleanup can fail without a server traceback. |

The upgrade helper is a starting point, not acceptance. It may touch JavaScript/XML literals but cannot decide
whether a component's props, lifecycle, service, or inherited template still has the same meaning.

### Visual proof

Load the affected action in a real browser, open the browser console, exercise initial render, prop changes,
empty/loading/error states, slot content, keyboard focus, and unmount/remount. Clear Odoo asset attachments or
use a fresh asset bundle before testing; otherwise an old bundle can hide the actual result.

For the conceptual Owl 2 → Owl 3 changes, also consult the [official Owl migration guide](https://github.com/odoo/owl/blob/master/doc/v3/owl/migration_owl2_to_owl3.md).

## 5. Constraints: important legacy finding, not a release mapping

Both source snapshots contain the same warning:

```text
Model attribute '_sql_constraints' is no longer supported,
please define models.Constraint on the model.
```

It appears in Odoo 19 at `odoo/orm/model_classes.py:162-164` and in Odoo 20 at
`odoo/orm/model_classes.py:175-177`. Therefore this repository must not teach `_sql_constraints` →
`models.Constraint` as if it were a new Odoo 20-only change. It is a legacy custom-code correction that may be
discovered during a 19→20 port and should be fixed before or during the port.

### Proof

Declare the constraint with the target-supported `models.Constraint`, upgrade the module, query
`pg_constraint`, and attempt a duplicate create/write in a disposable database. The expected visual effect is
an ordinary user receiving a validation error instead of seeing duplicate business codes; the expected database
effect is a named PostgreSQL constraint.

## 6. View-tag and modifier caveat

`<list>` versus `<tree>` and `attrs=` versus inline expressions are useful legacy scans, but they are not all
new Odoo 19→20 changes. Odoo 19 core already contains many `<list>` views, and Odoo 20 still contains isolated
legacy occurrences. Likewise, a raw `attrs=` count can include HTML attributes in Owl code rather than classic
server-view modifiers.

For each hit, identify the parser that consumes the file:

| Hit | Required check | Proof |
|---|---|---|
| `<tree>` in a server view | Convert only if the target view parser requires `<list>` | Open list view, inspect columns, grouping, inline edit, and inheritance |
| `attrs=` or `states=` in a server view | Convert the actual modifier domain to an inline expression using target fields | Test every state and access group |
| `attrs=` in Owl HTML | Keep/modify as a normal HTML attribute according to the component | Browser DOM and interaction test |

This classification prevents a scanner from producing false migration work or hiding a genuine view-parser
failure.

## Visual-effects matrix

| Source change | Browser symptom | Server/data symptom | Minimum proof |
|---|---|---|---|
| `_table_query` left behind | Report screen fails, is empty, or shows wrong totals | Missing relation/column, stale query, or unflushed source data | Registry + query + totals + drill-down |
| ACL CSV copied with old columns | Menu may open for admin but fail or overexpose for users | Wrong `ir.access` rows or domains | Role matrix with allow/deny cases |
| Owl/QWeb directive not transformed | Blank widget, missing slot/text, console exception | Usually no registry error | Fresh asset bundle + browser console + interaction |
| Legacy `_sql_constraints` retained | Form accepts duplicate code | `pg_constraint` absent | Duplicate write + catalog query |
| View hit misclassified | View inheritance or modifier silently differs | XML parse/load error or wrong arch | Full view tree + each state/role |

## Reusable review record

For every real port, record the evidence in this form:

```text
Artifact:
Odoo 19 source path and lines:
Odoo 20 source path and lines:
Confirmed release delta or legacy finding:
Code/data change:
Browser-visible effect:
Database/server effect:
Static proof:
Runtime proof:
Status: complete / deferred / blocked with reason
```

This is the boundary between a useful migration example and a plausible-looking snippet. The target source,
the disposable database, and the browser must all agree.
