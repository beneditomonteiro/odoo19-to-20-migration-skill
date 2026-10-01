# Odoo 19 → 20 migration problems and solutions

This catalog records problems found during real migration work. It is a fast diagnostic reference:
identify the symptom, apply the corresponding class of fix, and run the stated proof. Examples are
generalized so the document can be shared publicly.

## Reference and environment problems

### 1. The reference database was not defined

**Problem:** A familiar database name was initially treated as the migration reference even though its
business scope and installed modules did not match the code being ported.

**Solution:** Select the reference by business domain and installed-module inventory. Record source
revision, installed versions, database identity, and representative accounting totals before editing code.

**Proof:** A Gate G0 record containing identity checks, module inventory, pre-migration totals, and a
reproducible restore command.

### 2. Backups were not sufficient evidence by themselves

**Problem:** A successful dump command does not prove that the correct database or filestore was captured.

**Solution:** Keep an immutable raw restore and a separate sanitized working copy. Hash both database and
filestore artifacts. Never sanitize the only copy.

**Proof:** SHA-256 manifests, restore logs, row-count checks, attachment samples, and a documented
raw-to-sanitized relationship.

### 3. Odoo 19 and Odoo 20 stacks were easy to mix

**Problem:** A migration command can accidentally use the wrong config, PostgreSQL cluster, addons path,
or service process.

**Solution:** Give Odoo 20 its own code tree, configuration, HTTP port, PostgreSQL cluster, filestore,
and database naming convention. Verify the one-shot command and browser-facing service separately.

**Proof:** Printed config values, `pg_stat_activity`, process command line, runtime addon provenance, and
database version checks.

### 4. One-shot upgrade and live service used different addons paths

**Problem:** A command-line upgrade succeeded, but the browser service loaded a different module tree.

**Solution:** Inspect the actual service command/config and the one-shot command independently. Confirm the
ported source appears in both addon paths before accepting the result.

**Proof:** Runtime module provenance and a browser-visible module upgrade after restart.

### 5. Missing or malformed addon paths were silently ignored

**Problem:** A nonexistent addon directory can be skipped without making the root cause obvious.

**Solution:** Validate every configured directory, ensure it contains modules, and fail the deployment
check when an expected path is absent.

**Proof:** Path existence checks plus `ir.module.module` provenance.

### 6. Version strings prevented modules from being installable

**Problem:** A copied module retained an Odoo 19 version prefix and was silently treated as incompatible or
not installable.

**Solution:** Change the manifest major-version prefix immediately after copying, before the first install.

**Proof:** Manifest inventory and installed module version query.

### 7. Full upgrades were too slow for iteration

**Problem:** Repeating a full upgrade for every small fix dominated working time.

**Solution:** Use targeted one- or two-module upgrades while iterating; reserve full-suite upgrades for
phase gates and release rehearsals.

**Proof:** Targeted logs for local iteration and a separate full-suite gate log.

## Silent ORM and schema problems

### 8. `_sql_constraints` silently stopped creating constraints

**Problem:** Odoo 20 logged a warning but loaded the module without the intended database constraint.

**Solution:** Replace declarations with `models.Constraint` and verify PostgreSQL `pg_constraint` directly.

**Proof:** Constraint query, duplicate-value test, and clean upgrade log.

### 9. `_table_query` was removed

**Problem:** Virtual report/reconciliation models failed during registry construction.

**Solution:** Use `_table_sql` and Odoo 20 SQL/query objects. For a pure placeholder model, use a safe
empty SQL relation; for a real report, rebuild and validate every selected column.

**Proof:** Registry load plus report rendering and SQL-column checks.

### 10. `hr.leave.type` was removed as a model

**Problem:** A search-and-replace left invalid model metadata, XML IDs, relations, views, domains, or
absence/payroll semantics.

**Solution:** Create a business-approved data map to `hr.work.entry.type`, then migrate XML IDs, fields,
views, reports, and wizards with idempotent pre/post steps.

**Proof:** Model registry, XML-ID map, populated leave/work-entry sample, and payroll calculation.

### 11. Core model replacement was mistaken for an API rename

**Problem:** `hr.contract.type` records survived in metadata while Odoo 20 expected `hr.employee.type`.

**Solution:** Rename the table/sequence where present and update `ir.model`, `ir.model.fields`, relations,
XML-ID model values, and foreign-key columns such as `contract_type_id`.

**Proof:** Registry load and metadata/column queries.

### 12. Field changes were discovered only when a record was used

**Problem:** Static imports passed, but runtime access failed for removed fields or changed computed fields.

**Solution:** Build a registry-backed field inventory and exercise create/write/search/report paths for every
extended core model. Do not rely only on import scanners.

**Proof:** Model field assertions and representative transaction tests.

### 13. `company_type` and `is_company` semantics changed

**Problem:** Code read removed `company_type`, or attempted to create a company by writing computed,
read-only `is_company` without the data required by its computation.

**Solution:** Use current `is_company` semantics. For imports that create companies without VAT, reapply
the intended state after creation in the owning business module and test later recomputation.

**Proof:** Person/company creation and VAT update tests.

### 14. Character-size truncation disappeared

**Problem:** Odoo 19 silently truncated `fields.Char(size=...)`; Odoo 20 let PostgreSQL reject oversized
values.

**Solution:** Decide whether the limit is a business rule. Explicitly validate or truncate at the writer,
and retain the database size only when appropriate.

**Proof:** Boundary tests for accepted and rejected values.

### 15. Unit-of-measure fields were renamed

**Problem:** Dictionary keys and runtime field access using `product_uom_id` or `product_uom` failed.

**Solution:** Use `uom_id` for the affected purchase/stock models, while preserving fields that did not
change, such as `account.move.line.product_uom_id`.

**Proof:** Purchase, stock move, and stock move-line create/update tests.

## Access, rules, and security problems

### 16. Access control moved from `ir.model.access`/`ir.rule` to `ir.access`

**Problem:** Existing XML IDs referred to the old model, and conversion could produce invalid `model_id`
values or change rule semantics.

**Solution:** Convert ACL operations to `c/r/u/d`, expand grouped rules, represent global rules as
restrictions, relink XML IDs, then repair unresolved model names. Review rule unions manually.

**Proof:** Effective-rights comparison by group, not just row counts; run the rule-preservation checker.

### 17. Group rules changed meaning when combined with ACL permissions

**Problem:** A rule that was restrictive in Odoo 19 could become permissive when represented as a grouped
permission row in Odoo 20.

**Solution:** Decide per rule whether it is a group permission or group-less restriction. Preserve rules
with dynamic domains manually when the converter cannot represent them.

**Proof:** Non-admin multi-company and record-visibility tests.

### 18. Odoo test users were not administrators

**Problem:** Tests that created actions or configuration records failed under the Odoo 20 test user.

**Solution:** Use `.sudo()` only around the protected creation operation, and set test user groups
explicitly for logic tests. Keep dedicated access tests non-sudo.

**Proof:** Separate functional and access-control test cases.

### 19. x2many values were filtered by the reader's access

**Problem:** A user could see a count but receive an empty related recordset because the linked model had
no read access. `compute_sudo=True` did not solve every read path.

**Solution:** Grant intended read access or perform a narrowly scoped sudo read where the business process
explicitly requires it.

**Proof:** The same scenario tested as administrator and restricted user.

## View, report, and data-loader problems

### 20. Restored databases contained stale view rows

**Problem:** Views from removed modules, old inheritance parents, and copy-on-write views failed when Odoo
20 validated the complete view tree.

**Solution:** Classify views as kept, parked, recreated, or deleted. Clear stale inheritance metadata only
for the controlled migration, preserve foreign-key-referenced views, and reactivate/validate parked views
after the first successful upgrade.

**Proof:** A migration view inventory and a second upgrade after reactivation.

### 21. Standard accounting report XML IDs were renamed

**Problem:** Recreating standard lines, expressions, or columns collided with Odoo 20 uniqueness rules.

**Solution:** Remove standard-owned rows/XML IDs so Odoo 20 source recreates them; keep custom report rows
and protect cash-flow references.

**Proof:** Report structure query, unique-key check, and rendered report comparison.

### 22. Report columns became database-unique

**Problem:** Custom handlers that ignored `expression_label` had multiple columns using the same label.

**Solution:** Give every column a unique `(report_id, expression_label)` pair after confirming the handler
does not depend on the old duplicate value.

**Proof:** `pg_constraint` and report output.

### 23. Multi-line domain formulas failed stricter parsing

**Problem:** Trailing whitespace or malformed multi-line `engine="domain"` formulas passed Odoo 19 but
failed Odoo 20 literal evaluation.

**Solution:** Normalize and parse every formula before loading. Do not hide syntax errors with broad
exception handling.

**Proof:** Data-file parser and rendered report tests.

### 24. View buttons were checked against actual methods

**Problem:** `type="object"` buttons referenced methods that no longer existed; `toggle_active` was also
removed from the expected API.

**Solution:** Resolve every button against the target model. Use the supported active field widget or
`action_archive`/`action_unarchive` methods.

**Proof:** Clean view load and click tests.

### 25. `t-esc` and `t-raw` no longer rendered as expected

**Problem:** Templates loaded but output was blank or unsafe because old directives were removed/changed.

**Solution:** Convert to `t-out` and test HTML, text, reports, email, and portal rendering separately.

**Proof:** Rendered-output assertions, not only XML parsing.

### 26. Attachment binary behavior changed

**Problem:** `ir.attachment.datas` and direct base64 assumptions created empty attachments or broken downloads.

**Solution:** Use `raw` for bytes and `BinaryValue.content` when reading binary fields. Preserve filename and
content-type behavior.

**Proof:** Create, read, RPC, download, and filestore-resolution tests.

### 27. Configuration parameters became typed

**Problem:** A string such as `"False"` remained truthy, or XML still called removed `set_param`.

**Solution:** Choose `get_bool`, `get_str`, `get_int`, or `get_float` per parameter and update XML data
functions to the matching `set_*` method. Review automatic rewrites by hand.

**Proof:** True/false, empty/default, numeric, and XML-load tests.

### 28. Translation language was not active

**Problem:** Data files using a translation context failed with an invalid-language error on a fresh DB.

**Solution:** Create the disposable database with the required language active before loading translated
data, or load the language in the documented order.

**Proof:** Fresh-database install with the intended language set.

## Frontend, Owl, POS, and assets

### 29. Registry and HTTP checks missed browser-only failures

**Problem:** Removed Owl metadata or renamed QWeb inheritance parents produced a blank screen or JavaScript
exception without a server traceback.

**Solution:** Run a real browser gate for every migrated action and inspect the console. Test the exact
asset bundle generated after the change.

**Proof:** Browser screenshots, console log, and bundle hash captured with the test result.

### 30. The official Owl migration script was not a complete port

**Problem:** It generated invalid imports, wrong `this.` additions, unused template directives, skipped
inherit-only templates, and removed copyright comments.

**Solution:** Run official transforms one at a time, review the diff, restore required headers, and hand-fix
Owl state, refs, listeners, slots, and inheritance.

**Proof:** Static scan plus browser test; never accept the script exit code alone.

### 31. FontAwesome CSS was gone

**Problem:** Old icons rendered as empty boxes or wrong glyphs.

**Solution:** Map each icon to an available Odoo icon or Material Symbol, include the required classes/data
attribute, and verify visually. Unknown icons must be reported, not guessed.

**Proof:** Browser glyph checklist.

### 32. QUnit and frontend test conventions changed

**Problem:** Old test files were not discovered or used removed helpers.

**Solution:** Move to Hoot, the correct test bundle, `*.test.js`, and current mail model setup.

**Proof:** A test-run result showing discovery and zero failures.

### 33. POS and account-report patches were structurally incompatible

**Problem:** Changing imports left old jQuery/widget lifecycle assumptions and obsolete POS payment hooks.

**Solution:** Rebuild on the Odoo 20 owner component/order-push lifecycle. Test offline mode, retries,
duplicates, multi-record flows, and browser behavior.

**Proof:** End-to-end browser and transaction tests.

## Removed models and integrations

### 34. `res.bank` no longer existed

**Problem:** `_inherit = "res.bank"` failed during registry construction.

**Solution:** Provide a small local compatibility model only when required, with reviewed fields and a
`models.Constraint` for the code.

### 35. Barcode mixin and widget were removed

**Problem:** Modules inheriting `barcodes.barcode_events_mixin` or using `barcode_handler` failed to load.

**Solution:** Add a local scanned-value field/onchange and a current Owl barcode plugin integration, or
remove the feature if it is not in scope.

### 36. Seller selection returned a dictionary

**Problem:** `seller.partner_id` and `seller.price` raised attribute errors.

**Solution:** Read dictionary keys and use the supplied `supplierinfo` record when a record is required.

### 37. Odoo 19-only dependencies had no Odoo 20 source

**Problem:** A clean target registry could still contain installed modules whose source was unavailable.

**Solution:** Produce a disposition matrix: port, disable with approval, or remove with documented data
cleanup. Do not call the database clean because target modules load.

**Proof:** Installed-module inventory, disposition approval, and orphan-view audit.

## Test and acceptance problems

### 38. A baseline was claimed even when tests had not run

**Problem:** A green-looking report hid skipped or undiscovered tests.

**Solution:** Record test collection, selected tags, pass/fail counts, and whether the baseline failure is
pre-existing or introduced.

**Proof:** Raw test output and collection summary.

### 39. Test order changed after migration

**Problem:** Tests that ran before sibling modules were installed on Odoo 19 now ran later and encountered
new accounting/location constraints.

**Solution:** Repair fixtures or explicitly tag tests for the intended install phase. Do not weaken business
constraints just to preserve old test order.

### 40. A baseline test referenced invalid data already on Odoo 19

**Problem:** A missing unit-of-measure category caused a baseline failure unrelated to Odoo 20.

**Solution:** Classify it as a pre-existing baseline defect, fix the fixture or document it, and do not count
it as evidence against the migration.

### 41. Technical success was confused with functional acceptance

**Problem:** Registry load and module installation did not prove invoice totals, tax posting, reports,
reconciliation, payroll, POS sync, browser behavior, security, performance, or rollback.

**Solution:** Require representative workflows and expected values from the Odoo 19 reference, plus browser,
security, backup/restore, and rollback gates.

**Proof:** A signed acceptance matrix with evidence for every business area.

## Additional API and data-loader findings

These smaller compatibility breaks were easy to miss because they appeared only after a larger blocker
was removed:

| Problem | Resolution |
|---|---|
| `Query` moved from `odoo.tools` | Import it from `odoo.models`. |
| `content_disposition` moved from `odoo.http` | Import it from `odoo.http.stream`. |
| `check_method_name` disappeared | Remove the import and call; do not invent a replacement guard. |
| `tools.ormcache` / `tools.cache` only warn | Use `api.ormcache`. |
| Registry cache-clearing helpers disappeared | Use `env.transaction.invalidate_ormcache()` with the correct cache name. |
| `api.propagate` disappeared | Remove it with the obsolete `@api.returns` dependency. |
| Request session/database helper disappeared | Use current router database selection and the supported database header behavior. |
| PostgreSQL retry constant moved | Use the exception-class constant from `odoo.sql_db`. |
| Official `ir.access.csv` conversion left unresolved model XML IDs | Run the model resolver/fixer and inspect every unresolved row. |
| Official conversion handled only the first duplicate `foldable` field | Grep and convert every remaining occurrence manually. |
| Official Owl transform emitted `t-custom-ref` | Remove or rewrite it according to the current Owl template API. |
| Missing customer modules left orphaned views | Build a module disposition and clean orphan records deliberately. |

Each row requires a source-level check plus the relevant registry, schema, browser, or functional proof;
none should be accepted solely because the process exits with status zero.

## Final release lesson

The most expensive mistakes came from trusting the nearest symptom: a `KeyError` that was really an
inactive language, a clean registry that concealed a missing constraint, a clean one-shot upgrade that used
another addons path, and a claimed baseline whose tests had not run. The reliable pattern is:

1. identify the exact source and data scope;
2. freeze and hash a copy;
3. inventory statically;
4. use current Odoo source and official transforms as references;
5. verify schema and effective permissions;
6. exercise the browser and business workflows;
7. record evidence before calling the migration complete.
