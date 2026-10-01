# custom Odoo: Odoo 19 to Odoo 20 Migration Guide

**Language:** American English
**Date:** September 25, 2026
**Scope:** custom Odoo custom modules and their Odoo Enterprise dependencies
**Status:** Migration assessment and implementation plan; the custom Odoo modules have not yet been ported to Odoo 20.

## 1. Executive summary

This guide defines the work required to migrate the custom Odoo custom modules from Odoo 19 to Odoo 20. It is based on a local comparison of:

- Odoo 19 Enterprise snapshot: $ODOO19_ROOT/enterprise19_0919
- Odoo 20 Enterprise snapshot: $ODOO20_ROOT/enterprise20_0924
- custom Odoo custom source currently available at: $ODOO19_ROOT/maxdoo_ao

There is no $ODOO20_ROOT/maxdoo_ao directory in the current workspace. Therefore, this document is a migration guide and technical assessment, not evidence that the custom modules already work on Odoo 20.

The highest-risk areas are:

1. Legacy JavaScript in max_l10n_ao_report, which still uses odoo.define, require("web.core"), core.action_registry, jQuery, and the old account report widget inheritance model.
2. Owl 2 assumptions in max_3panel_reconciliation, especially static props and dependency-array useEffect calls, while the Odoo 20 web client contains an Owl 2-to-Owl 3 compatibility layer.
3. Custom SQL/report models using _table_query, which is removed from the Odoo 20 ORM direction and must be rewritten with the current SQL/query APIs.
4. Odoo 19 Enterprise overrides and patches that target classes, files, or methods moved in Odoo 20.
5. Remaining legacy XML modifiers (attrs and states) in the Maxdoo source.
6. POS, HR, accounting-report, and localization code that depends on internal APIs and must be tested against the Odoo 20 implementation rather than copied mechanically.

The recommended approach is an incremental migration on a new Odoo 20 branch and disposable database, with the localization foundation migrated first, followed by shared partner/HR/report modules, then sales/stock/POS, and finally integrations.

## 2. Sources and comparison method

### 2.1 Local source trees

The comparison used the following local directories:

| Purpose | Path |
|---|---|
| Odoo 19 Enterprise | $ODOO19_ROOT/enterprise19_0919 |
| Odoo 20 Enterprise | $ODOO20_ROOT/enterprise20_0924 |
| custom Odoo custom modules | $ODOO19_ROOT/maxdoo_ao |
| Odoo 20 Community source | $ODOO20_ROOT/odoo |

The two Enterprise directories are snapshots, not a substitute for reading the Odoo 20 implementation of every class being customized. A file existing in both snapshots does not guarantee API compatibility.

### 2.2 Important scope finding

The Enterprise snapshots do not contain the custom Odoo modules. The custom modules are in $ODOO19_ROOT/maxdoo_ao, and no equivalent Odoo 20 copy was found under $ODOO20_ROOT.

The migration work must therefore:

1. Copy or branch the Maxdoo source into an Odoo 20 development location.
2. Port the source module by module.
3. Install the port into a disposable Odoo 20 database.
4. Upgrade and test it before any customer or production database is considered.

## 3. custom Odoo module inventory

The current custom Odoo tree contains these top-level modules:

- l10n_ao
- l10n_ao_complete
- l10n_ao_stocks
- max_3panel_reconciliation
- max_agt_prospector
- max_l10n_ao_account_asset
- max_l10n_ao_account_iva
- max_l10n_ao_dashboards
- max_l10n_ao_erc_intercompany_bridge
- max_l10n_ao_hr
- max_l10n_ao_hr_holidays
- max_l10n_ao_partner_base
- max_l10n_ao_payroll_plus
- max_l10n_ao_pos
- max_l10n_ao_report
- max_l10n_ao_sale
- max_l10n_ao_stocks

The manifest review shows the following logical dependency layers:

| Layer | Modules | Migration purpose |
|---|---|---|
| 1 | l10n_ao | Angola localization foundation, accounting data, taxes, fiscal behavior |
| 2 | max_l10n_ao_partner_base | Partner and customer extensions used by other modules |
| 3 | max_l10n_ao_hr, max_l10n_ao_hr_holidays, max_l10n_ao_payroll_plus | HR, time off, payroll and employee extensions |
| 4 | max_l10n_ao_report, max_l10n_ao_account_asset, max_l10n_ao_account_iva, max_l10n_ao_dashboards | Accounting reports, assets, IVA, and dashboards |
| 5 | max_l10n_ao_sale, max_l10n_ao_stocks, l10n_ao_stocks | Sales, stock, and Angola stock behavior |
| 6 | max_l10n_ao_pos | Point of Sale customizations |
| 7 | max_3panel_reconciliation, max_agt_prospector, max_l10n_ao_erc_intercompany_bridge | Reconciliation UI, external/operational tools, and integrations |
| 8 | l10n_ao_complete | Aggregated installation package |

The exact installation order must be generated from the manifests after the Odoo 20 branch is created. Do not assume that the order above is a complete dependency graph.

## 4. Compatibility summary

| Area | Verified Odoo 19 or Maxdoo pattern | Odoo 20 direction | Action | Priority |
|---|---|---|---|---|
| Web framework | Legacy odoo.define, require, jQuery and old widgets in max_l10n_ao_report | Owl 3 components, ES modules, registries and services | Rewrite the affected feature | Critical |
| Owl components | static props, dependency-array useEffect in max_3panel_reconciliation | Owl 3 useProps, signal-based effects, compatibility bridge only as a temporary step | Port and test hooks | Critical |
| Account reports | Old accountReportsWidget.extend | AccountReport, AccountReportController, custom component registration | Rebuild report UI extension | Critical |
| SQL/report models | _table_query in Maxdoo and Odoo 19 Enterprise patterns | Odoo 20 removes _table_query; use current query/SQL patterns | Rewrite report models | Critical |
| XML views | attrs=, states= in Maxdoo files | Inline Python expressions such as invisible="state != 'draft'" | Convert and validate views | High |
| ORM | Older aliases and deprecated internals may remain | Use current env, recordsets, domains, and public APIs | Static scan plus functional review | High |
| Binary fields | Code may assume a base64 string | Odoo 20 exposes BinaryValue with content, filename, size and conversion helpers | Review every binary attachment flow | High |
| Icons | Old Font Awesome classes in Enterprise snapshots | Material Symbols and Odoo UI Icons (oi) | Replace custom icon references | Medium |
| Assets | Asset bundles and JavaScript paths changed between snapshots | Use the Odoo 20 manifest and asset declarations | Rebuild assets per module | High |
| POS | Patch targets and method paths are internal and version-sensitive | Verify Odoo 20 POS class and data APIs | Port and test online/offline flows | Critical |
| Security | Existing access rules may not cover new models or fields | Recheck ACLs, record rules, routes, and sudo calls | Security review before release | Critical |

## 5. Owl 2 to Owl 3 migration

### 5.1 What the local Odoo 20 source shows

The Odoo 20 Community source contains:

$ODOO20_ROOT/odoo/addons/web/static/src/owl2/owl3_compatibility_layer.js

Its comments explicitly describe a temporary Owl 2-to-Owl 3 compatibility layer. The local implementation warns about these migrations:

- Replace t-portal with t-custom-portal while using the compatibility bridge; later migrate to the proper Owl 3 portal approach.
- Replace t-model with t-custom-model while using the compatibility bridge; later migrate to the Owl 3 approach.
- Replace dependency-array useEffect usage with useLayoutEffect during the bridge period, then review each effect and migrate it to the appropriate Owl 3 pattern.
- Replace class-level static props and static defaultProps with useProps inside the component setup.
- Do not treat the compatibility layer as a permanent target. It is a staging tool for incremental migration.

Odoo 20 code also uses import { Component, t, useProps } from "@odoo/owl" and the normal Odoo registries and services.

### 5.2 Maxdoo example: static props

Current file:

$ODOO19_ROOT/maxdoo_ao/max_3panel_reconciliation/static/src/components/bank_rec_classic/kanban.js

The component declares static props and inherits KanbanController.props. That is an Owl 2-style assumption.

Typical migration shape:

Odoo 19-style pattern:

~~~javascript
export class BankRecKanbanController extends KanbanController {
    static props = {
        ...KanbanController.props,
        skipRestore: { optional: true },
    };
}
~~~

Odoo 20/Owl 3-oriented pattern:

~~~javascript
import { useProps } from "@odoo/owl";

export class BankRecKanbanController extends KanbanController {
    setup() {
        super.setup(...arguments);
        this.props = useProps({
            ...KanbanController.props,
            skipRestore: { optional: true },
        });
    }
}
~~~

The exact useProps shape must be verified against the Odoo 20 base controller used by the module. Do not blindly copy this skeleton if the parent controller exposes a different props contract.

The compatibility file states that Owl 3 ignores class-level static props and static defaultProps. Leaving the old declaration in place can therefore produce missing or incorrectly validated props.

### 5.3 Maxdoo example: useEffect

The same kanban.js file uses calls shaped like:

~~~javascript
useEffect(() => {
    this.onWillStartAfterLoad();
}, () => []);

useEffect(() => {
    // React to the selected reconciliation page.
}, () => [this.state.bankRecNotebookPage]);
~~~

This dependency-array behavior is not the safe Odoo 20 target. The Odoo 20 source comments that Owl 3 useEffect takes a single callback and that a dependency argument is silently ignored. A callback must read the signals or reactive values on which it depends, or the code should use an appropriate change hook.

Migration procedure:

1. Determine whether the callback must run before rendering, after rendering, or when a specific field changes.
2. For a layout-sensitive effect during transitional work, use the Odoo compatibility bridge only after confirming the local Odoo 20 implementation.
3. For a real Owl 3 port, use the current hook semantics and read the reactive state inside the effect.
4. For a specific field-change reaction, use the Odoo 20-supported change mechanism rather than preserving the old dependency-array syntax.
5. Add a browser test for initial load, page switching, record save, and controller destruction.

### 5.4 Template directives

Search the Maxdoo source for:

- t-model
- t-portal
- t-on-*
- t-ref
- t-component
- t-inherit

Any t-model or t-portal occurrence must be reviewed against the Odoo 20 Owl 3 rules. During an incremental port, the compatibility names may be required, but the final code should use the native Odoo 20/Owl 3 pattern where possible.

### 5.5 Keep the modern parts

max_3panel_reconciliation already contains modern Odoo-style code in places. For example:

$ODOO19_ROOT/maxdoo_ao/max_3panel_reconciliation/static/src/components/bank_rec_classic/list.js

uses:

- ES module imports
- ListController
- a view definition based on listView
- registry.category("views").add(...)
- useChildSubEnv

This is a better starting point than the legacy account report implementation. Port the minimum required API changes, then validate the controller and model signatures in Odoo 20.

## 6. Account reports: highest-risk frontend migration

### 6.1 Current Maxdoo implementation

File:

$ODOO19_ROOT/maxdoo_ao/max_l10n_ao_report/static/src/js/account_reports.js

The file combines two incompatible generations of frontend code:

~~~javascript
registry.category('actions').add('l10n_ao_account_report', l10nAoAccountReport);

odoo.define("max_l10n_ao_report.account_report", function (require) {
    "use strict";
    var core = require("web.core");
    var accountReport = require("account_reports.account_report");
    var QWeb = core.qweb;

    var l10nAoAccountReportsWidget = accountReport.accountReportsWidget.extend({
        start: async function () {
            await this._super.apply(this, arguments);
        },
        parse_report_informations: function (values) {
            this._super(...arguments);
        },
    });

    core.action_registry.add(
        "l10n_ao_account_report",
        l10nAoAccountReportsWidget
    );
});
~~~

The actual file contains additional jQuery event handling and old widget behavior. The important migration findings are:

- registry is referenced before the modern import that should define it.
- odoo.define and require("web.core") belong to the legacy module system.
- accountReportsWidget.extend and _super belong to the old widget architecture.
- core.qweb, core.action_registry, and direct jQuery manipulation must not be treated as Odoo 20 APIs.
- The same feature should not be registered once through the modern action registry and again through the legacy action registry.

### 6.2 Odoo 20 target architecture

The Odoo 20 Enterprise source uses:

- $ODOO20_ROOT/enterprise20_0924/account_reports/static/src/components/account_report/account_report.js
- $ODOO20_ROOT/enterprise20_0924/account_reports/static/src/components/account_report/controller.js

The account report frontend is based on Owl components and the action registry. The Odoo 20 implementation exports an AccountReport component and an AccountReportController. Current account report extensions in Enterprise register custom components through the controller's custom-component mechanism.

Migration target pattern:

~~~javascript
/** @odoo-module **/

import { AccountReportController } from "@account_reports/components/account_report/controller";
import { AccountReportFilters } from "@account_reports/components/account_report/filters/filters";

export class L10nAoAccountReportFilters extends AccountReportFilters {
    // Add only the Angola-specific filter behavior.
}

AccountReportController.registerCustomComponent(
    L10nAoAccountReportFilters
);
~~~

This is a migration skeleton, not a drop-in replacement. The exact extension point must be selected after comparing the Odoo 20 account report template, controller, model, and filter component used by the target report.

Recommended port:

1. Identify which user-visible requirement the legacy code provides: account selector, custom filter, report action, or additional columns.
2. Locate the corresponding Odoo 20 component or controller hook.
3. Create a small Owl component or patch the documented/current class.
4. Add an XML template using Odoo 20 template inheritance.
5. Register the component exactly once.
6. Move server communication to the current ORM/service or account report model API.
7. Remove direct DOM manipulation wherever a component state or template can express the behavior.
8. Test the report with no filter, one account, multiple accounts, date changes, company changes, export, and browser refresh.

Do not port this file by changing only import paths. The old widget lifecycle and the Odoo 20 account report component lifecycle are different.

## 7. POS patch review

File:

$ODOO19_ROOT/maxdoo_ao/max_l10n_ao_pos/static/src/js/PaymentScreen.js

The current customization patches _postPushOrderResolve and calls a custom model method:

~~~javascript
/** @odoo-module **/

import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { patch } from "@web/core/utils/patch";
import { session } from "@web/session";

patch(PaymentScreen.prototype, {
    async _postPushOrderResolve(order, order_server_ids) {
        if (this.pos.company.country_id.code == "AO") {
            const result = await this.pos.data.call(
                "pos.order",
                "get_res_company",
                [order_server_ids]
            );
            order.set_software_id = result;
        }
        return super._postPushOrderResolve(...arguments);
    },
});
~~~

Risks to resolve during the Odoo 20 port:

- session is imported but unused.
- The POS class path and _postPushOrderResolve signature are version-sensitive.
- this.pos.data.call must be checked against the Odoo 20 POS data API.
- order.set_software_id = result assigns a value to a property with a method-like name. Confirm whether this is intended to set a field, call a method, or update a server-side value.
- Use strict comparison and null-safe access for the country code.
- Confirm whether the call must happen before or after the standard push-order resolution.
- Test the behavior when the call fails, the device is offline, the order is retried, and the order contains multiple server IDs.

A safer review target is:

~~~javascript
const countryCode = this.pos.company.country_id?.code;
if (countryCode === "AO") {
    // Use the Odoo 20 POS data API after verifying its contract.
}
~~~

Do not assume that the Odoo 19 method still exists in Odoo 20. Search the Odoo 20 POS source for the current order-push lifecycle and patch the method that actually owns the required behavior.

## 8. SQL reports and _table_query

### 8.1 Odoo 20 change

The Odoo 20 ORM changelog removes Model._table_query. The Odoo 20 direction uses SQL/query objects and explicit initialization patterns. The local Odoo 20 source includes examples using:

- from odoo.tools import SQL
- from odoo.models import TableSQL
- from odoo.fields import Domain
- _auto = False
- init() with self.env.cr.execute(SQL(...))
- query and domain APIs where appropriate

The Odoo 20 Enterprise sale/report/sale_report.py is a concrete example of a newer query-oriented implementation. Compared with Odoo 19, it imports Domain, TableSQL, and SQL, and builds a typed query through _table_sql, _order_line_domain, and select dictionaries.

### 8.2 Maxdoo hotspots

The Maxdoo source contains _table_query in:

- $ODOO19_ROOT/maxdoo_ao/max_3panel_reconciliation/models/bank_rec_widget.py
- $ODOO19_ROOT/maxdoo_ao/max_3panel_reconciliation/models/bank_rec_widget_line.py

These files must be rewritten rather than left unchanged.

Migration procedure:

1. Identify the SQL view columns and the corresponding Odoo fields.
2. Confirm whether the model is a read-only SQL view (_auto = False) or a normal stored model.
3. Find the nearest Odoo 20 core or Enterprise implementation with the same report purpose.
4. Replace _table_query with the Odoo 20-supported initialization/query structure.
5. Use SQL(...) composition and parameters instead of unsafe string interpolation.
6. Validate every selected SQL column against information_schema.columns.
7. Upgrade the exact disposable target database.
8. Confirm that list views, search domains, grouping, sorting, pagination, and reconciliation actions still work.

Do not invent a new helper name merely to preserve the old code. Use the current Odoo 20 pattern that matches the model's purpose.

## 9. XML view migration

### 9.1 Legacy modifiers in Maxdoo

The Maxdoo source still contains attrs= and states= patterns. Known examples include:

- $ODOO19_ROOT/maxdoo_ao/l10n_ao/views/account_vat_tax.xml
- $ODOO19_ROOT/maxdoo_ao/max_l10n_ao_hr/views/hr_payslip_views.xml
- $ODOO19_ROOT/maxdoo_ao/max_l10n_ao_hr_holidays/wizard/holiday_map.xml

There are also states= references in:

- $ODOO19_ROOT/maxdoo_ao/l10n_ao/views/account_vat_tax.xml
- $ODOO19_ROOT/maxdoo_ao/max_l10n_ao_hr/models/hr_payslip_inherit.py

Replace old modifiers with inline expressions.

Before:

~~~xml
<field name="amount"
       attrs="{'invisible': [('state', '!=', 'draft')],
               'readonly': [('state', '=', 'done')]}"/>
~~~

After:

~~~xml
<field name="amount"
       invisible="state != 'draft'"
       readonly="state == 'done'"/>
~~~

For a button:

~~~xml
<button name="action_confirm"
        type="object"
        invisible="state != 'draft'"/>
~~~

Review every expression in context. The field names must be available to the view, and the expression must match the Odoo 20 view evaluator semantics.

### 9.2 Lists and tree views

Odoo 20 uses <list> for list views. Search all XML for old <tree> declarations and replace them with <list> while preserving the relevant attributes and child fields. Validate each view after conversion rather than relying on a global text replacement.

### 9.3 Icons

The Odoo 20 UI documentation identifies Material Symbols as the primary icon system and Odoo UI Icons (oi) as the supplementary Odoo-specific set. Font Awesome compatibility is not a safe long-term target.

Before:

~~~xml
<i class="fa fa-check"/>
~~~

Odoo 20-oriented example:

~~~xml
<i class="oi" data-icon="check"/>
~~~

Search custom XML, JavaScript templates, CSS, and SCSS for fa fa-, fa-, and hard-coded icon assumptions. Validate the visual result in the browser because an icon class can remain syntactically valid while rendering the wrong glyph.

## 10. Binary fields and attachments

Odoo 20's local ORM defines BinaryValue for binary fields. It exposes information including:

- content
- filename
- mimetype
- size
- checksum
- to_base64()
- open()

Custom code that assumes a binary field is always a plain base64 string must be reviewed.

Preferred read pattern:

~~~python
file_value = record.file_field
if file_value:
    raw_content = file_value.content
    original_filename = file_value.filename
    payload_base64 = file_value.to_base64()
~~~

When writing a binary value with a filename, use the Odoo 20 field contract and test it:

~~~python
record.write({
    "file_field": {
        "content": file_content,
        "filename": "document.pdf",
    },
})
~~~

The exact accepted content type depends on the field conversion path. Test bytes, base64 input, RPC input, and download responses separately. Do not silently discard filenames; this can change customer-facing downloads and report attachments.

Review:

- document uploads
- invoice attachments
- XML/SAF-T or fiscal files
- employee documents
- POS receipts
- report exports
- any controller that returns a binary response

## 11. ORM and server-side API review

Perform a full static and functional review for these patterns:

- direct use of record._cr
- direct use of record._context
- direct use of record._uid
- name_get
- old read_group implementations
- _table_query
- raw SQL string interpolation
- sudo() without an explicit security reason
- model methods called from JavaScript with undocumented argument shapes
- fields created without migration/default handling
- computed fields missing correct dependencies
- api.onchange logic incorrectly relied on for server-side validation

Prefer:

- self.env.cr where direct cursor access is actually required
- self.env.context
- self.env.uid
- current ORM methods and domains
- _read_group or the Odoo 20-supported grouping API where applicable
- parameterized SQL(...)
- explicit access checks and narrowly scoped sudo()

This review is not limited to syntax. A deprecated method may still import successfully but behave differently, return a different data structure, or bypass a newer security rule.

## 12. Enterprise 19 versus Enterprise 20: concrete changes

### 12.1 Payment customization

Odoo 19 Enterprise file:

$ODOO19_ROOT/enterprise19_0919/payment_custom/static/src/interactions/post_processing.js

The old customization patches PaymentPostProcessing and adds a final state for the custom provider.

Odoo 20 Enterprise file:

$ODOO20_ROOT/enterprise20_0924/payment_custom/static/src/interactions/payment_form.js

The new code patches PaymentForm.prototype and changes the pay-later behavior. The file path, class, method, and patch target all changed.

Migration rule:

- Find the Odoo 20 class that owns the behavior.
- Read the current method implementation.
- Port the business rule to that method.
- Do not copy an Odoo 19 patch and only change the import path.
- Test all payment states, including pending, authorized, cancelled, failed, and paid.

### 12.2 Sale report implementation

Odoo 19 Enterprise uses the older sale report SQL assembly style with _select_sale, _with_sale, _select_additional_fields, and large SQL strings.

Odoo 20 Enterprise uses query-oriented helpers and introduces fields and joins that are not present in the old implementation. It imports Domain, TableSQL, and SQL, and exposes a _table_sql property built from a current Odoo query.

Migration rule:

- Compare every custom field and group-by value with the Odoo 20 report.
- Rebase custom additions on the Odoo 20 implementation.
- Do not merge the old report file wholesale into Odoo 20.
- Verify report results against known sales orders, deliveries, invoices, analytic accounts, tags, and dates.

### 12.3 Binary and translations

The Odoo 20 ORM adds BinaryValue handling, and the changelog also records changes to translation manipulation and manifest translation storage. Review:

- binary field conversion
- exported/imported translations
- module translation files
- manifest terms
- copied name fields and default “(copy)” behavior
- any custom code that edits ir.translation directly

## 13. Asset and manifest migration

For every custom module:

1. Confirm the manifest version is Odoo 20-compatible.
2. Update the version to the agreed Odoo 20 versioning convention.
3. Verify dependencies against Odoo 20 module names.
4. Replace removed or renamed dependencies.
5. Rebuild assets declarations from actual Odoo 20 files.
6. Remove obsolete JavaScript files from assets.
7. Avoid loading the same file through multiple bundles.
8. Verify backend, frontend, POS, report, and website assets separately.
9. Upgrade the module with asset debug enabled.
10. Test in a clean browser session after clearing stale assets.

Example migration checks:

~~~bash
rg -n 'odoo\.define|require\(["'\'']web\.|core\.action_registry|core\.qweb|static props|useEffect|t-model|t-portal|attrs=|states=|_table_query|<tree|fa fa-' \
    /path/to/maxdoo_ao
~~~

Use the exact Odoo 20 addons path for the target instance. In the current local Odoo 20 setup, the relevant paths are:

~~~ini
addons_path = $ODOO20_ROOT/enterprise20_0924,$ODOO20_ROOT/odoo/addons,$ODOO20_ROOT/odoo/odoo/addons
~~~

The configured $ODOO19_ROOT/oca_migrated_20/web path should only be kept if it exists and is intentionally part of the Odoo 20 installation.

## 14. Recommended migration plan

### Phase 0: Freeze and baseline

- Create a dedicated Odoo 20 migration branch for Maxdoo.
- Record the exact Odoo 19 and Odoo 20 source revisions.
- Back up the source database and filestore.
- Export a module dependency inventory from every manifest.
- Record installed module versions and custom data files.
- Do not test the first migration against production or a customer database.

### Phase 1: Static inventory

Run a source scan and classify each result:

- legacy JavaScript module system
- Owl 2 API
- XML modifier
- SQL/report API
- ORM/deprecation
- security/access rule
- data migration
- external integration
- performance-sensitive code

Assign each item an owner and test case. Treat comments and documentation matches as false positives only after manual verification.

### Phase 2: Port the localization foundation

Port and install:

1. l10n_ao
2. localization data and tax/account mappings
3. l10n_ao_complete only after the foundation works

Verify:

- chart of accounts
- tax groups and taxes
- fiscal positions
- journals and sequences
- partner fiscal fields
- invoice posting
- credit notes
- refunds
- fiscal/legal reports
- multi-company behavior
- Portuguese and English translations

### Phase 3: Port shared models

Port:

- max_l10n_ao_partner_base
- common models and mixins
- access rules
- views and menus
- server actions
- scheduled actions

At this phase, resolve field renames, computed fields, constraints, and security groups before porting larger frontend features.

### Phase 4: Port accounting and reporting

Port:

- max_l10n_ao_report
- max_l10n_ao_account_asset
- max_l10n_ao_account_iva
- max_l10n_ao_dashboards
- max_3panel_reconciliation

Rewrite the legacy account report frontend and _table_query models. Validate totals against a fixed Odoo 19 reference dataset.

### Phase 5: Port sales, stock, HR, and payroll

Port:

- max_l10n_ao_sale
- max_l10n_ao_stocks
- l10n_ao_stocks
- max_l10n_ao_hr
- max_l10n_ao_hr_holidays
- max_l10n_ao_payroll_plus

Test workflows, not only module installation:

- quotation to sales order
- delivery and backorder
- invoice and credit note
- stock valuation
- employee onboarding
- time off approval
- payslip computation
- accounting entries generated by each workflow

### Phase 6: Port POS and integrations

Port last:

- max_l10n_ao_pos
- max_agt_prospector
- max_l10n_ao_erc_intercompany_bridge

Test:

- POS opening and closing
- offline orders
- payment retry
- fiscal information
- order synchronization
- duplicate prevention
- integration timeout and retry
- permissions and secret handling

### Phase 7: Database migration

Only after the module code installs cleanly:

1. Restore a copy of the Odoo 19 database into a disposable Odoo 20 PostgreSQL database.
2. Run the Odoo-supported database upgrade path.
3. Install or upgrade the Odoo 20 custom modules.
4. Resolve schema and data migration errors.
5. Inspect all changed field columns in information_schema.columns.
6. Run business reconciliation against the Odoo 19 reference exports.
7. Test the filestore and all binary downloads.
8. Repeat with a fresh copy until the process is deterministic.

### Phase 8: Acceptance and release

The release candidate must pass:

- module installation from an empty database
- module upgrade from the migrated database
- Python tests
- JavaScript tests
- browser tours or Playwright scenarios
- accounting reconciliation
- stock reconciliation
- HR/payroll reconciliation
- security review
- performance smoke tests
- backup and restore test
- log review with no unexplained traceback

## 15. Testing commands

Use commands adapted to the actual service account, configuration, and database. Do not run them against production until the disposable database passes.

Module installation:

~~~bash
python3 $ODOO20_ROOT/odoo/odoo-bin \
    -c $ODOO20_CONFIG \
    -d maxdoo_ao_20_migration \
    -i l10n_ao,max_l10n_ao_partner_base \
    --without-demo=all \
    --stop-after-init \
    --no-http
~~~

Module upgrade:

~~~bash
python3 $ODOO20_ROOT/odoo/odoo-bin \
    -c $ODOO20_CONFIG \
    -d maxdoo_ao_20_migration \
    -u l10n_ao,max_l10n_ao_partner_base \
    --stop-after-init \
    --no-http
~~~

Test mode:

~~~bash
python3 $ODOO20_ROOT/odoo/odoo-bin \
    -c $ODOO20_CONFIG \
    -d maxdoo_ao_20_migration \
    -u l10n_ao_complete \
    --test-enable \
    --stop-after-init \
    --no-http
~~~

Static checks:

~~~bash
rg -n 'odoo\.define|require\(|web\.core|action_registry|core\.qweb|static props|static defaultProps|useEffect\([^)]*,|t-model|t-portal|attrs=|states=|_table_query|name_get|read_group|_cr|_context|_uid' \
    $ODOO19_ROOT/maxdoo_ao
~~~

Database schema verification:

~~~sql
SELECT table_name, column_name, data_type
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name IN ('res_partner', 'account_move', 'account_move_line')
ORDER BY table_name, ordinal_position;
~~~

The exact table list must be expanded for each changed model. After any model field change, verify the target database columns before trusting the migration.

## 16. Risk register

| Risk | Affected area | Impact | Mitigation |
|---|---|---|---|
| Legacy account report widget cannot load | max_l10n_ao_report | Report page fails or remains blank | Rewrite as Odoo 20 Owl component/controller extension |
| Owl 2 props/effects silently behave differently | max_3panel_reconciliation | Incorrect UI state or runtime errors | Replace static props; rewrite effects; add browser tests |
| SQL view no longer initializes | reconciliation/report models | Missing model/table or broken grouping | Rewrite _table_query; validate SQL and schema |
| POS method moved | max_l10n_ao_pos | Fiscal/POS information missing or duplicate calls | Verify Odoo 20 POS source and push-order lifecycle |
| Old XML modifier rejected or ignored | localization, HR, time off | Incorrect visibility/editability | Convert attrs and states; install views on a clean database |
| Binary filename lost | attachments and exports | Customer receives unnamed or invalid files | Port to BinaryValue; test RPC and download paths |
| Patch targets an internal Enterprise API | payment/report/sale | Upgrade breaks behavior silently | Rebase each patch on the Odoo 20 implementation |
| Excessive sudo() or missing ACLs | custom models and integrations | Data exposure or access failures | Review ACLs and record rules with non-admin users |
| Asset cache hides the real result | all frontend modules | Old code appears to work or new code appears broken | Use asset debug, clean browser profiles, and fresh bundles |
| Data migration changes accounting totals | localization and reports | Compliance and reconciliation failure | Fixed reference dataset, accounting reconciliation, dual review |

## 17. Definition of done

The custom Odoo migration is complete only when all of the following are true:

- The Odoo 20 branch contains the custom source under a controlled addons path.
- Every module manifest installs on a clean Odoo 20 database.
- No critical legacy JavaScript module-system use remains.
- Owl components use the Odoo 20-supported props and hook patterns.
- Account report customizations use the Odoo 20 account report component architecture.
- _table_query implementations are ported to the current Odoo 20 SQL/query approach.
- XML modifiers use Odoo 20 syntax and all views load without warnings.
- POS, accounting, stock, HR, payroll, and integration workflows pass business tests.
- Database fields and indexes are verified after migration.
- Access rights and record rules pass tests with representative user roles.
- Binary files preserve their contents and filenames.
- Accounting balances and operational totals reconcile with the Odoo 19 reference.
- Browser tests cover the critical custom screens.
- A backup and restore test succeeds.
- The release package includes migration scripts, release notes, test evidence, and rollback instructions.

## 18. Official technical references

Use the official Odoo 20 documentation together with the local source code:

- Odoo 20 source installation: https://www.odoo.com/documentation/20.0/administration/on_premise/source.html
- Odoo 20 web framework tutorial: https://www.odoo.com/documentation/20.0/developer/tutorials/master_odoo_web_framework/02_create_gallery_view.html
- Odoo 20 UI icons: https://www.odoo.com/documentation/20.0/developer/reference/user_interface/icons.html
- Odoo ORM changelog, including the Odoo 20 section: https://www.odoo.com/documentation/master/developer/reference/backend/orm/changelog.html
- Local Owl 2-to-Owl 3 bridge: $ODOO20_ROOT/odoo/addons/web/static/src/owl2/owl3_compatibility_layer.js
- Local Odoo 20 account report component: $ODOO20_ROOT/enterprise20_0924/account_reports/static/src/components/account_report/account_report.js
- Local Odoo 20 account report controller: $ODOO20_ROOT/enterprise20_0924/account_reports/static/src/components/account_report/controller.js

## 19. Final recommendation

Begin with a dedicated Odoo 20 Maxdoo branch and a disposable database. Port l10n_ao and shared models first, then rebuild the account report and reconciliation frontend before attempting the full package. The legacy report frontend and SQL report models are the main blockers; they should be treated as code migrations, not compatibility edits.

Do not deploy the current Odoo 19 Maxdoo source into Odoo 20 unchanged. The Enterprise comparison shows real changes to frontend class ownership, payment patch targets, report SQL construction, binary values, icons, and the Owl runtime. A controlled port with automated installation, schema checks, accounting reconciliation, and browser tests is required.
