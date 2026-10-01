# Static-first procedure

The migration order is deliberately static first, install last:

1. Freeze the Odoo 19 source revision, target Odoo 20 revision, database dump, and filestore.
2. Build a manifest/dependency inventory and an Odoo-19-only dependency disposition matrix.
3. Run the pattern scan, import checker, inheritance-target checker, access CSV checker, and registry-env checker.
4. Apply only reviewed official upgrade-code transforms, then inspect their complete diff.
5. Port Python/ORM, XML/data, JavaScript/Owl, assets, security, and reports in dependency order.
6. Run syntax, XML, static, and unit checks before creating a migration database.
7. Restore a copy into an isolated Odoo 20 PostgreSQL cluster and run pre-migration data preparation.
8. Upgrade targeted modules, verify registry state, columns, constraints, XML IDs, and logs.
9. Run browser, accounting, stock, HR/payroll, POS, security, attachment, backup, and rollback gates.

The following patterns require explicit review:

| Odoo 19 pattern | Odoo 20 treatment | Proof required |
|---|---|---|
| legacy `_sql_constraints` | `models.Constraint` (supported in current Odoo 19 and Odoo 20) | `pg_constraint` query |
| `_table_query` | `_table_sql` with Odoo 20 SQL/query objects | registry + report output |
| server-view `attrs=` / `states=` | inline expressions where required; classify Owl HTML attributes separately | clean view load + browser |
| legacy server-view `<tree>` | `<list>` where required; do not treat as a blanket 19→20 conversion | clean view load |
| `t-esc` / `t-raw` | `t-out` | rendered output |
| `get_param` / `set_param` | typed getters/setters | type-specific behavior |
| `ir.attachment.datas` | `raw` / `BinaryValue.content` | upload/download test |
| `ir.model.access.csv` + rules | `ir.access.csv` | effective-rights comparison |
| Owl 2 | Owl 3 | browser test |
| FontAwesome | Odoo icons/Material Symbols | browser glyph check |
