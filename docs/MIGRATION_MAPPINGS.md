# Odoo 19 → 20 migration mappings

This is the quick mapping register. A mapping is not automatically safe: confirm the target model,
field semantics, XML IDs, business meaning, and existing data before applying it.

## Core data and XML-ID mappings

| Odoo 19 | Odoo 20 | Treatment |
|---|---|---|
| `ir.model.access` | `ir.access` | Convert model permissions to operation strings `c/r/u/d`; move XML IDs. |
| `ir.rule` with groups | `ir.access` permission rows | Create one row per group and preserve the domain. |
| Global `ir.rule` | group-less `ir.access` restriction | Preserve restrictive semantics; review rule unions manually. |
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
| `_sql_constraints` | `models.Constraint` | Rewrite and verify the actual PostgreSQL constraint. |
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

## Custom-module correspondence used by the reference port

The reference localization had two different relationships: CE was mostly a rename-fork, while CTB was
an architectural rewrite. The names below are examples of the correspondence that must be recorded rather
than inferred:

| Source module | CE target | CTB target(s) |
|---|---|---|
| `l10n_ao` | `l10n_ao_ce` | `l10n_ao` |
| `l10n_ao_complete` | `l10n_ao_ce_complete` | `l10n_ao_complete_ctb` |
| `l10n_ao_stocks` field extension | merged into CE stocks | `maxdoo_ao_inventory_base` |
| `max_3panel_reconciliation` | `max_ce_3panel_reconciliation` | same name |
| `max_agt_prospector` | `max_ce_agt_prospector` | same name |
| `max_l10n_ao_account_asset` | CE equivalent | `maxdoo_ao_fixed_assets_base`, `maxdoo_ao_fixed_assets` |
| `max_l10n_ao_account_iva` | CE equivalent | absorbed into `l10n_ao` |
| `max_l10n_ao_dashboards` | CE equivalent | same name |
| `max_l10n_ao_erc_intercompany_bridge` | CE equivalent | same name |
| `max_l10n_ao_hr` | CE equivalent | `maxdoorh_ao_hr_base`, `_absences`, `_payroll` |
| `max_l10n_ao_hr_holidays` | CE equivalent | `maxdoorh_ao_hr_absences` |
| `max_l10n_ao_partner_base` | CE equivalent | same name |
| `max_l10n_ao_payroll_plus` | CE equivalent | `maxdoorh_ao_hr_payroll_plus` |
| `max_l10n_ao_pos` | CE equivalent | same name |
| `max_l10n_ao_report` | CE equivalent | `maxdoo_ao_fixed_assets`, `l10n_ao` |
| `max_l10n_ao_sale` | CE equivalent | `maxdoo_ao_revenues_base`, `maxdoo_ao_revenues` |
| `max_l10n_ao_stocks` | CE equivalent | `maxdoo_ao_inventory_base`, `maxdoo_ao_inventory` |

The two stock rows are intentionally different: one tracks a field-level legacy extension and the other
tracks the full picking rewrite. Document ownership explicitly to prevent double migration.
