# Odoo core artifact changes: 19 → 20

This report intentionally excludes project-specific module names, customer data, and organization-specific
bugs. It describes the core artifacts that a migration must inspect: source declarations, database metadata,
XML/data records, frontend assets, and runtime behavior.

The key rule is that an artifact can remain syntactically valid while its meaning changes. Every row below
therefore includes a migration implication and a proof, not only a replacement string.

| Core artifact | Odoo 19 | Odoo 20 | Migration implication and proof |
|---|---|---|---|
| Database constraints | `_sql_constraints` model declaration | `models.Constraint` | Rewrite declarations; query `pg_constraint`; test duplicate data. |
| Virtual SQL models | `_table_query` | `_table_sql` using current SQL/query objects | Rebuild report/reconciliation queries; verify columns and rendered output. |
| Model access | `ir.model.access` | `ir.access` | Convert permissions to `c/r/u/d`; move XML IDs; compare effective rights. |
| Record rules | `ir.rule` with grouped/global semantics | `ir.access` permission/restriction rows | Decide per rule whether it is a permission or restriction; test non-admin visibility. |
| Field indexes | `true` / `false` strings | `btree`, `btree_not_null`, `trigram`, or `NULL` | Normalize stored metadata before registry setup. |
| Contract type model | `hr.contract.type` | `hr.employee.type` | Migrate table, metadata, relations, XML-ID model values, and foreign-key columns. |
| Leave type model | `hr.leave.type` | Role represented by `hr.work.entry.type` | Create an explicit data/XML-ID mapping; do not use a global text replacement. |
| Approval manager flag | Selection values such as `required` | Boolean | Define the business mapping and review whether `approver` should become `true`. |
| Country-state XML ID | Old XML ID may remain in the database | Renamed XML ID | Relink the existing row before loading the new base data. |
| Moved XML IDs | Record owned by the old module | Record defined by a different module | Move only when exactly one installed target module defines the ID. |
| Renamed XML IDs | Old identifier in the database | New identifier in source | Match by a unique stable business code; report ambiguity instead of guessing. |
| Standard report structure | Existing standard lines/expressions/columns | New XML IDs and uniqueness rules | Remove standard-owned rows so Odoo 20 recreates them; retain custom rows. |
| Report-column identity | Duplicate expression labels could load | Unique `(report_id, expression_label)` | Give independent columns distinct labels and verify the database constraint. |
| Report formulas | More permissive domain parsing | Stricter literal parsing | Remove trailing whitespace and validate every multi-line formula before loading. |
| Report file naming | `ir.actions.report.report_file` available | Removed or redundant with `report_name` | Delete only after confirming equivalent `report_name` behavior. |
| View inheritance | Old parent links and stale combined arches may survive | Whole view tree validated at load | Classify views as keep, park, recreate, or delete; run a second validation. |
| View modifiers | `attrs=` and `states=` | Inline Python expressions | Convert and validate each view against the current model fields. |
| List views | `<tree>` | `<list>` | Convert tags and verify list behavior in the browser. |
| Kanban templates | `kanban-box` | `card` | Update templates and run a browser smoke test. |
| Object buttons | Button names sometimes resolved late | Method existence validated against the model | Check every `type="object"`; replace removed archive helpers. |
| QWeb escaping | `t-esc`, `t-raw` | `t-out` | Convert directives and render text, HTML, reports, and emails. |
| Owl component metadata | Owl 2 `static props` | Owl 3 component contract/`useProps` patterns | Hand-review official transform output and browser-test components. |
| Owl state | `useState`, `useRef`, old listener helpers | Current proxy/signal/listener APIs | Rewrite lifecycle and ref reads against the installed Owl source. |
| Owl slots | `t-slot` | `t-call-slot` | Convert templates and test inherited/inherit-only templates. |
| Account reports frontend | Legacy widget/jQuery/registry patterns | Owl report components and controllers | Rebuild lifecycle and service usage; changing imports alone is insufficient. |
| POS frontend | Older payment/order-push hooks | Current order-push lifecycle | Rebase patches on Odoo 20 source; test offline, retries, duplicates, and multi-order flows. |
| JavaScript tests | QUnit conventions | Hoot and current test bundles | Rename/discover tests using the Odoo 20 browser test runner. |
| Icons | FontAwesome CSS subset | Odoo icons and Material Symbols | Map only to shipped glyphs and verify visually in a browser. |
| Binary attachments | `ir.attachment.datas`, direct base64 assumptions | `raw` bytes and `BinaryValue.content` | Update reads/writes; test RPC, filename, content type, download, and filestore. |
| Configuration parameters | Untyped `get_param` / `set_param` | Typed `get_*` / `set_*` methods | Select type from business semantics; update Python and XML data files. |
| Bank model | `res.bank` available for inheritance | Removed from base | Add a minimal compatibility model only if the business feature needs it. |
| Partner bank fields | `acc_number`, `currency_id` available in old views | `account_number`; `currency_id` removed | Re-anchor inherited views on current Odoo 20 fields. |
| Company registry | Standard field available | Removed from base | Redeclare locally only when statutory/business output requires it. |
| Analytic report filter | `filter_analytic` | `filter_analytic_groupby` | Update XML records and live template attribute reads. |
| Partner company type | Computed `company_type` | Use current `is_company` semantics | Update business logic and test creation/recomputation paths. |
| Partner/mobile/type fields | Some legacy fields remain readable | `mobile` and `detailed_type` removed in affected models | Resolve every field through the target registry and test runtime paths. |
| Character fields | `size=` could truncate in conversion | Oversized values can reach PostgreSQL | Validate or truncate explicitly at the business writer. |
| Seller selection | Seller result treated as record-like | `_select_seller()` returns a dictionary | Read dictionary keys and use the supplied supplier record when needed. |
| Stock/purchase UoM fields | Several model-specific `product_uom*` names | Affected fields use `uom_id` | Update dictionaries, domains, related fields, and runtime accesses. |
| Barcode integration | Barcode mixin/widget available | Removed in the affected API | Implement a current plugin/field integration or retire the feature deliberately. |
| Registry cache APIs | Older cache-clear helpers | Transaction cache invalidation API | Update callers and specify the correct cache scope. |
| HTTP database selection | Older request/session helper | Current router/header behavior | Remove monkey patches and use the supported database-selection flow. |
| PostgreSQL retry constants | Error-code-oriented constant | Exception-class-oriented constant | Update imports and `isinstance` handling. |
| ORM decorators | `api.propagate` and older return helpers | Removed | Remove obsolete decorators and adapt the method contract. |
| Test access context | Tests often ran as administrator | `BaseCommon` is not automatically admin | Use narrow sudo for setup and explicit groups for access tests. |
| Related record reads | x2many values appeared available to callers | Reader ACLs filter related values | Test counts and recordsets separately; grant/read as intended. |
| Installed modules | Source availability often assumed | Odoo 19-only modules may have no Odoo 20 source | Build a port/disable/remove disposition before declaring a database clean. |
| Filestore/database restore | Dump success treated as completeness | Missing objects, users, or permissions can remain | Keep raw/sanitized copies, hash artifacts, test login, attachments, and permissions. |

## Minimum proof for a changed artifact

1. Static scan or source diff identifies the old artifact.
2. Current Odoo 20 source confirms the replacement semantics.
3. Targeted upgrade completes with `Modules loaded` and `Registry loaded`.
4. `information_schema.columns` and `pg_constraint` confirm stored schema/constraints.
5. XML IDs, access rights, and data cardinality are compared.
6. Browser and business workflow tests exercise the changed path.
7. Backup, rollback, and release evidence are recorded.
