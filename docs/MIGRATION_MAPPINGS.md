# Odoo 19 → 20 migration mappings

This is the quick mapping register. A mapping is not automatically safe: confirm the target model,
field semantics, XML IDs, business meaning, and existing data before applying it.

## Core data and XML-ID mappings

| Odoo 19 | Odoo 20 | Treatment |
|---|---|---|
| `ir.model.access` | `ir.access` | Convert the old `perm_*` CSV columns to target `operation`/`domain` data; move XML IDs. |
| `ir.rule` with groups | reviewed `ir.access` permission/restriction rows | Preserve the domain and decide whether the target row grants or restricts access; do not assume one row is equivalent. |
| Global `ir.rule` | reviewed group-less `ir.access` restriction | Preserve restrictive semantics; review rule unions manually. |
| `ir.model.fields.index = true` | `btree` | Normalize before registry setup. |
| `ir.model.fields.index = false/''` | `NULL` | Normalize before registry setup. |
| `base.state_in_or` | `base.state_in_od` | Relink the existing state record to avoid duplicate country/code data. |
| `hr.contract.type` | `hr.employee.type` | Rename table, model metadata, relations, and XML-ID model references. |
| `hr.version.contract_type_id` | `employee_type_id` | Rename column and metadata. |
| `hr.job.contract_type_id` | `employee_type_id` | Rename column and metadata. |
| `approval_category.manager_approval` selection | Boolean | Map `required` and `approver` to `true`; review the stricter interpretation. |
| `hr.leave.type` | `hr.work.entry.type` | Build an explicit XML-ID/data map; this is not a text replacement. |
| XML ID moved to another module | new owning module | Detect only when exactly one installed target module defines it. |
| XML ID renamed inside one module | new XML ID | Match by a unique stable business code; never guess ambiguous matches. |
| Standard report lines/expressions/columns | Odoo 20 XML definitions | Remove standard rows/XML IDs and let the new source recreate them; retain custom rows. |
| Stale standard/gone/COW views | Odoo 20 view tree | Park, deactivate, delete, or recreate according to ownership and foreign-key references. |
| `crm_iap_mine` industry reference data | Odoo 20 industry data | Remove stale relation/XML-ID/reference rows before module reload. |

## ORM/API mappings

| Odoo 19 | Odoo 20 | Resolution |
|---|---|---|
| `_sql_constraints` in legacy custom code | `models.Constraint` | This is already the supported form in current Odoo 19 and Odoo 20; convert the legacy declaration and verify `pg_constraint`, but do not call it a new 19→20 release mapping. |
| `_table_query` | `_table_sql` | Rebuild using current Odoo 20 SQL/query APIs. |
| `from odoo.tools import Query` | `from odoo.models import Query` | Update import. |
| `odoo.http.content_disposition` | `odoo.http.stream.content_disposition` | Update import. |
| `check_method_name` | removed | Delete the import/call; rely on the current dispatch API. |
| `get_param` / `set_param` | `get_str`, `get_bool`, `get_int`, `get_float` / `set_*` | Choose the type from business semantics, not the key name alone. |
| `res.bank` inheritance | local compatibility model | Redeclare only the fields/data actually required by the module. |
| `res.partner.bank.acc_number` | `account_number` | Update inherited views and code. |
| `res.partner.bank.currency_id` | removed | Remove or redesign the dependency. |
| `res.company.company_registry` | removed from base | Redeclare locally when the business process requires it. |
| `account.report.filter_analytic` | `filter_analytic_groupby` | Update data and template attribute reads. |
| `account.report.line.foldable` | `foldability` selection | Convert every occurrence; inspect official script output for duplicate fields. |
| `account.report.column` duplicate labels | unique `(report_id, expression_label)` | Give custom columns distinct labels when the handler does not consume them. |
| `ir.actions.report.report_file` | removed/redundant | Delete only after confirming `report_name` is equivalent. |
| `res.partner.company_type` | `is_company` | Remove the old field and adapt logic to current computed semantics. |
| `res.partner.mobile`, `crm.lead.mobile` | removed | Use supported phone/contact fields. |
| `product.template.detailed_type` | `type` | Update reads, writes, domains, and views. |
| `registry.clear_*_caches()` | `env.transaction.invalidate_ormcache()` | Use the current cache API and cache name. |
| `api.propagate` | removed | Remove the decorator/API dependency. |
| `PG_CONCURRENCY_ERRORS_TO_RETRY` | `PG_CONCURRENCY_EXCEPTIONS_TO_RETRY` | Update import and exception handling. |
| `Request._get_session_and_dbname` | router database selection | Use the current router and `X-Odoo-Database` behavior. |
| `barcodes.barcode_events_mixin` / `barcode_handler` | removed | Implement a reviewed local scan field/widget if required. |
| `purchase.order.line.product_uom_id` | `uom_id` | Update field keys and runtime access. |
| `stock.move.product_uom` | `uom_id` | Update field keys and runtime access. |
| `stock.move.line.product_uom_id` | `uom_id` | Update field keys and runtime access. |
| `product._select_seller()` record | dictionary | Read `seller["price"]`, `seller["uom_id"]`, etc. |

## Frontend and asset mappings

| Odoo 19 | Odoo 20 | Resolution |
|---|---|---|
| Owl 2 `static props` | Owl 3 `useProps`/current component contract | Hand-review generated code. |
| Owl 2 `useState` | Owl 3 reactive `proxy` pattern | Verify against the vendored Owl source. |
| Owl refs | `signal.ref()` and `t-ref="this.x"` | Read refs as `this.x()`. |
| `useExternalListener` | `useListener` | Update import and lifecycle behavior. |
| `t-slot` | `t-call-slot` | Update templates. |
| `t-esc`, `t-raw` | `t-out` | Render-test every report, mail, and portal path. |
| FontAwesome CSS classes | Odoo icons/Material Symbols | Use the provided 107-entry icon register and browser-check glyphs. |
| QUnit | Hoot | Rename tests, use the correct test bundle, and run browser tests. |
| `kanban-box` | `card` | Update kanban templates. |
| Old account-report jQuery widget | Owl `AccountReport`/controller components | Rebuild the component lifecycle, not just imports. |
| Old POS payment patch hooks | Current order-push lifecycle | Rebase on Odoo 20 POS source and test offline/retry/multi-order cases. |

## Module mapping rules

Module names are evidence, not a migration plan. A source module may be renamed, split, merged into a
foundation module, replaced by standard Odoo functionality, or deliberately deferred. Record the mapping
explicitly rather than inferring it from a similar name.

For every source module, record:

- one or more target modules, or the explicit disposition `absorbed`, `replaced`, `deferred`, or `removed`;
- source and target manifest versions and dependencies;
- model, table, field, XML-ID, security, and asset ownership;
- the data migration needed when ownership changes;
- the installation, upgrade, schema, and browser proof for the target.

If a source module is split, map each model and XML-ID separately. If two source modules merge, identify the
single owner of each table, field, view, action, and data record so that the migration does not duplicate or
delete records. The public register intentionally omits project-specific module names.
